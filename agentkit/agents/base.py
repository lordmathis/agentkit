import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.agents.context import format_history, generate_title, parse_mentions
from agentkit.agents.context.skills import apply_skill_context, build_skill_context
from agentkit.db.db import Database
from agentkit.providers.provider import Provider
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agent types. Agents own their context and LLM interaction."""

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
    ):
        self.chat_id = chat_id
        self.db = db
        self.provider = provider
        self.tool_manager = tool_manager
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.tool_servers = list(tool_servers)
        self.skill_registry = skill_registry
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm_client = provider.get_llm_client()

    @abstractmethod
    async def _run(self, message: str) -> Dict[str, Any]:
        """Execute the agent's logic. Must be implemented by subclasses."""
        ...

    async def chat(self, message: str, file_ids: List[str] = []) -> Dict[str, Any]:
        """Main entry point. Handles persistence and naming automatically."""
        await self._save_message("user", message, file_ids=file_ids)
        response = await self._run(message)
        await self._save_message("assistant", response)
        asyncio.create_task(
            generate_title(self.chat_id, self.db, self._llm_client, self.model_id)
        )
        return response

    async def _save_message(
        self,
        role: str,
        content_or_response: str | Dict[str, Any],
        file_ids: List[str] = [],
    ) -> None:
        """Save a message to the database."""
        if role == "assistant":
            if isinstance(content_or_response, dict):
                if "error" in content_or_response:
                    content = f"Error: {content_or_response['error']}"
                    reasoning_content = None
                    tool_calls_json = None
                else:
                    choices = content_or_response.get("choices", [])
                    if choices:
                        msg_data = choices[0].get("message", {})
                        if isinstance(msg_data, dict):
                            content = msg_data.get("content", "") or ""
                            reasoning_content = msg_data.get("reasoning_content")
                        else:
                            content = getattr(msg_data, "content", "") or ""
                            reasoning_content = getattr(
                                msg_data, "reasoning_content", None
                            )
                        tool_calls = content_or_response.get("tool_calls_used")
                        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
                    else:
                        content = ""
                        reasoning_content = None
                        tool_calls_json = None
                    self.db.save_message(
                        self.chat_id,
                        "assistant",
                        content,
                        reasoning_content=reasoning_content,
                        tool_calls=tool_calls_json,
                    )
            else:
                self.db.save_message(self.chat_id, "assistant", content_or_response)
        else:
            file_ids_json = json.dumps(file_ids) if file_ids else None
            self.db.save_message(
                self.chat_id, "user", content_or_response, file_ids=file_ids_json
            )
            if file_ids:
                self.db.attach_files(file_ids)

    async def _build_context(self, message: str) -> List[ChatCompletionMessageParam]:
        """Build full context from DB history with skill context injected from @mentions."""
        mentioned_skills = parse_mentions(message)
        skill_context, required_tool_servers = build_skill_context(
            mentioned_skills, self.skill_registry
        )

        if required_tool_servers:
            new_servers = [
                s for s in required_tool_servers if s not in self.tool_servers
            ]
            if new_servers:
                self.tool_servers = self.tool_servers + new_servers
                self.db.update_chat(
                    self.chat_id, tool_servers=json.dumps(self.tool_servers)
                )
                logger.info(
                    f"Activated skill tool servers for chat {self.chat_id}: {new_servers}"
                )

        messages = format_history(self.db, self.chat_id)
        messages = apply_skill_context(messages, skill_context)

        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                messages.insert(0, {"role": "system", "content": self.system_prompt})

        return messages

    async def _get_tools(self, servers: List[str]) -> List[dict]:
        """Get OpenAI-formatted tool definitions for the given servers."""
        api_tools = []
        for tool_server in servers:
            tools = await self.tool_manager.list_tools(tool_server)
            for tool in tools:
                if hasattr(tool, "parameters"):
                    parameters = tool.parameters
                else:
                    parameters = {}
                api_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"{tool_server}__{tool.name}",
                            "description": tool.description,
                            "parameters": parameters,
                        },
                    }
                )
        return api_tools

    async def _llm(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Make a single LLM call and return the raw response dict."""
        return await self._llm_client.chat_completion(
            model=self.model_id,
            messages=messages,
            tools=tools if tools else None,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def _get_history(self) -> List:
        """Get raw DB messages for manual context building."""
        return self.db.get_chat_history(self.chat_id)

    async def retry(self) -> Dict[str, Any]:
        """Retry the last message by deleting the last assistant response and re-processing."""
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
            self.db.delete_message(last_assistant.id)

        response = await self._run(last_user.content)
        await self._save_message("assistant", response)
        return response

    async def edit(self, new_message: str) -> Dict[str, Any]:
        """Edit the last user message and re-process."""
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
        self.db.delete_message(last_user.id)

        if last_assistant:
            self.db.delete_message(last_assistant.id)

        self.db.save_message(self.chat_id, "user", new_message, file_ids=file_ids_str)

        response = await self._run(new_message)
        await self._save_message("assistant", response)
        return response
