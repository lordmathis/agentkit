import json
import logging
from typing import Any, Dict, List, Optional

from agentkit.agents.base import BaseAgent
from agentkit.db.db import Database
from agentkit.providers.provider import Provider
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.approval import ToolDeniedError
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class ReActAgent(BaseAgent):
    """ReAct agent: iterative think -> act -> observe loop."""

    def __init__(
        self,
        chat_id: str,
        db: Database,
        provider: Provider,
        tool_manager: ToolManager,
        model_id: str,
        system_prompt: str = "",
        tool_servers: List[str] = [],
        skill_registry: Optional[SkillRegistry] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_iterations: int = 5,
    ):
        super().__init__(
            chat_id=chat_id,
            db=db,
            provider=provider,
            tool_manager=tool_manager,
            model_id=model_id,
            system_prompt=system_prompt,
            tool_servers=tool_servers,
            skill_registry=skill_registry,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.max_iterations = max_iterations

    async def chat(self, message: str, file_ids: List[str] = []) -> Dict[str, Any]:
        await self._save_message("user", message, file_ids=file_ids)
        result = await self._loop(message)
        await self._generate_title()
        return result

    async def _loop(self, message: str) -> Dict[str, Any]:
        messages = await self._build_context(message)
        tools = await self._get_tools(self.tool_servers)

        for _ in range(self.max_iterations):
            response = await self._llm(messages, tools if tools else None)
            message_data = response["choices"][0]["message"]

            if (
                not message_data.get("tool_calls")
                or len(message_data.get("tool_calls", [])) == 0
            ):
                await self._save_message("assistant", response)
                return response

            await self._save_message("assistant", response)

            tool_calls_raw = message_data["tool_calls"]
            messages.append(
                {
                    "role": "assistant",
                    "content": message_data.get("content"),
                    "tool_calls": tool_calls_raw,
                }
            )

            for tool_call in tool_calls_raw:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]

                if isinstance(tool_args_str, str):
                    tool_args = json.loads(tool_args_str)
                else:
                    tool_args = tool_args_str

                logger.debug(f"Calling tool: {tool_name}")

                try:
                    result = await self.tool_manager.call_tool(
                        tool_name, tool_args, self.provider, self.model_id, self.chat_id
                    )
                except ToolDeniedError as e:
                    result = f"Tool '{e.tool_name}' was denied by the user."

                await self._save_message(
                    "tool", str(result), tool_call_id=tool_call["id"]
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(result),
                    }
                )

        await self._save_message(
            "assistant", {"error": "Max iterations reached without final response"}
        )
        return {"error": "Max iterations reached without final response"}

    async def retry(self) -> Dict[str, Any]:
        history = self.db.get_chat_history(self.chat_id)
        last_assistant = None
        last_user = None
        for msg in reversed(history):
            if msg.role == "assistant" and last_assistant is None:
                last_assistant = msg
            elif msg.role == "user" and last_user is None:
                last_user = msg
            if last_assistant and last_user:
                break

        if not last_user:
            return {"error": "No user message to retry"}

        if last_assistant:
            for msg in history:
                if msg.role == "tool" and msg.sequence > last_assistant.sequence:
                    self.db.delete_message(msg.id)
            self.db.delete_message(last_assistant.id)

        return await self._loop(last_user.content)

    async def edit(self, new_message: str) -> Dict[str, Any]:
        history = self.db.get_chat_history(self.chat_id)
        last_user = None
        last_assistant = None
        for msg in reversed(history):
            if msg.role == "user" and last_user is None:
                last_user = msg
            elif msg.role == "assistant" and last_assistant is None:
                last_assistant = msg
            if last_user and last_assistant:
                break

        if not last_user:
            return {"error": "No user message to edit"}

        file_ids_str = getattr(last_user, "file_ids", None)
        file_ids = json.loads(file_ids_str) if file_ids_str else []

        if last_assistant:
            for msg in history:
                if msg.role == "tool" and msg.sequence > last_user.sequence:
                    self.db.delete_message(msg.id)
            self.db.delete_message(last_assistant.id)

        self.db.delete_message(last_user.id)
        await self._save_message("user", new_message, file_ids=file_ids)

        return await self._loop(new_message)


class ReActAgentPlugin(ReActAgent):
    """
    Base class for ReAct agent plugins.
    """

    default: bool = False
    name: str = ""
    provider_id: str = ""
    model_id: str = ""
    system_prompt: str = ""
    tool_servers: List[str] = []
    max_iterations: int = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def post_init(self) -> None:
        """Called after all dependencies are injected. Override for custom setup."""
        pass
