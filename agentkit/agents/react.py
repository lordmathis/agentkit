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

    async def _run(self, message: str) -> Dict[str, Any]:
        messages = await self._build_context(message)
        tools = await self._get_tools(self.tool_servers)
        all_tool_calls = []

        for _ in range(self.max_iterations):
            response = await self._llm(messages, tools if tools else None)
            message_data = response["choices"][0]["message"]

            if (
                not message_data.get("tool_calls")
                or len(message_data.get("tool_calls", [])) == 0
            ):
                if all_tool_calls:
                    response["tool_calls_used"] = all_tool_calls
                    logger.info(f"Tool calls tracked (success): {all_tool_calls}")
                return response

            messages.append(
                {
                    "role": "assistant",
                    "content": message_data.get("content"),
                    "tool_calls": message_data["tool_calls"],
                }
            )

            for tool_call in message_data["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]

                if isinstance(tool_args_str, str):
                    tool_args = json.loads(tool_args_str)
                else:
                    tool_args = tool_args_str

                logger.debug(f"Calling tool: {tool_name}")

                all_tool_calls.append(
                    {
                        "name": tool_name,
                        "arguments": tool_args,
                    }
                )

                try:
                    result = await self.tool_manager.call_tool(
                        tool_name, tool_args, self.provider, self.model_id, self.chat_id
                    )
                except ToolDeniedError as e:
                    result = f"Tool '{e.tool_name}' was denied by the user."

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(result),
                    }
                )

        result = {
            "error": "Max iterations reached without final response",
            "messages": messages,
        }
        if all_tool_calls:
            result["tool_calls_used"] = all_tool_calls
            logger.info(f"Tool calls tracked: {all_tool_calls}")
        return result


class ReActAgentPlugin(ReActAgent):
    """
    Base class for ReAct agent plugins.

    Override class attributes to configure the agent:

        class MyChatbot(ReActAgentPlugin):
            default = True
            provider_id = "llamactl"
            model_id = "my-model"
            system_prompt = "You are a helpful assistant."
            tool_servers = ["time"]

    For custom behavior, override post_init() and/or _run():

        class StructuredBot(ReActAgentPlugin):
            provider_id = "anthropic"
            model_id = "claude-sonnet-4-6"

            def post_init(self) -> None:
                self._parser = MyOutputParser()

            async def _run(self, message: str) -> Dict[str, Any]:
                response = await super()._run(message)
                return self._parser.parse(response)
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
