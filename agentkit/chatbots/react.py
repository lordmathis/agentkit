import json
import logging
from abc import ABC
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.chatbots.base import BaseAgent
from agentkit.providers.provider import Provider
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class ReActAgent(BaseAgent):
    """ReAct agent: iterative think → act → observe loop."""

    async def chat(self, messages: List[ChatCompletionMessageParam]) -> Dict[str, Any]:
        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                from openai.types.chat import ChatCompletionDeveloperMessageParam
                messages = [
                    ChatCompletionDeveloperMessageParam(
                        content=self.system_prompt, role="developer"
                    )
                ] + messages

        api_tools = []
        for tool_server in self.tool_servers:
            tools = await self.tool_manager.list_tools(tool_server)
            for tool in tools:
                if hasattr(tool, 'parameters'):
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
                        }
                    }
                )

        all_tool_calls = []

        for _ in range(self.max_iterations):
            response = await self.llm_client.chat_completion(
                model=self.model_id,
                messages=messages,
                tools=api_tools if api_tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            message = response["choices"][0]["message"]

            if not message.get("tool_calls") or len(message.get("tool_calls", [])) == 0:
                if all_tool_calls:
                    response["tool_calls_used"] = all_tool_calls
                    logger.info(f"Tool calls tracked (success): {all_tool_calls}")
                return response

            if self._check_tool_approvals_needed(message["tool_calls"]):
                return {
                    "pending_approval": True,
                    "tool_calls": [self._serialize_tool_call(tc) for tc in message["tool_calls"]],
                    "assistant_message": message,
                }

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": message["tool_calls"],
                }
            )

            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]

                if isinstance(tool_args_str, str):
                    tool_args = json.loads(tool_args_str)
                else:
                    tool_args = tool_args_str

                logger.debug(f"Calling tool: {tool_name}")

                all_tool_calls.append({
                    "name": tool_name,
                    "arguments": tool_args,
                })

                result = await self.tool_manager.call_tool(tool_name, tool_args, self.provider, self.model_id)

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


class ReActAgentPlugin(ReActAgent, ABC):
    """
    Base class for ReAct agent plugins.

    Override class attributes to configure the agent:

        class MyChatbot(ReActAgentPlugin):
            default = True
            provider_id = "llamactl"
            model_id = "my-model"
            system_prompt = "You are a helpful assistant."
            tool_servers = ["time"]
    """

    default: bool = False
    name: str = ""

    provider_id: str = ""
    model_id: str = ""
    system_prompt: str = ""
    tool_servers: List[str] = []
    max_iterations: int = 5
    temperature: Optional[float] = None
    max_tokens: Optional[float] = None

    def __init__(self, provider_registry: ProviderRegistry, tool_manager: ToolManager):
        super().__init__(
            provider=provider_registry.get_provider(self.provider_id),
            tool_manager=tool_manager,
            model_id=self.model_id,
            system_prompt=self.system_prompt,
            tool_servers=self.tool_servers,
            max_iterations=self.max_iterations,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
