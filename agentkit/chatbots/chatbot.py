import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from agentkit.providers.provider import Provider
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)

class Chatbot:
    """Base model for OpenAI-compatible chat with agent tool calling."""

    system_prompt: str = ""

    provider: Provider
    model_id: str = ""

    max_iterations: int = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    client: OpenAI

    def __init__(
        self,
        provider: Provider,
        tool_manager: ToolManager,
        model_id: str = "",
        system_prompt: str = "",
        tool_servers: List[str] = [],
        max_iterations: Optional[int] = 5,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.system_prompt = system_prompt
        self.provider = provider
        self.model_id = model_id
        self.tool_manager = tool_manager
        self.tool_servers = tool_servers
        self.max_iterations = max_iterations or 5
        self.temperature = temperature
        self.max_tokens = max_tokens

        client_kwargs = provider.get_client_kwargs()
        self.client = OpenAI(**client_kwargs)

    def name(self) -> str:
        return f"{self.provider}/{self.model_id}"

    async def chat(self, messages: List[ChatCompletionMessageParam]) -> Dict[str, Any]:
        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
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

        # Prepare API call params
        api_params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
        }

        if self.temperature is not None:
            api_params["temperature"] = self.temperature

        if self.max_tokens is not None:
            api_params["max_tokens"] = self.max_tokens

        if api_tools:
            api_params["tools"] = api_tools

        # Track all tool calls made during the conversation
        all_tool_calls = []

        for _ in range(self.max_iterations):
            # Call API
            response = self.client.chat.completions.create(**api_params)
            message = response.choices[0].message

            if not message.tool_calls or len(message.tool_calls) == 0:
                # Add tool calls metadata to the response if any were made
                result = response.model_dump()
                if all_tool_calls:
                    result["tool_calls_used"] = all_tool_calls
                    logger.info(f"Tool calls tracked (success): {all_tool_calls}")
                return result

            # Add assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            # Execute tool calls (run agents)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.debug(f"Calling tool: {tool_name}")

                # Record tool call
                all_tool_calls.append({
                    "name": tool_name,
                    "arguments": tool_args
                })

                result = await self.tool_manager.call_tool(tool_name, tool_args, self.provider, self.model_id)

                # Add tool result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

            # Update messages for next iteration
            api_params["messages"] = messages

            # Get response after tool execution
            response = self.client.chat.completions.create(**api_params)

        # Max iterations reached, add tool calls metadata and return error
        result = {
            "error": "Max iterations reached without final response",
            "messages": messages,
        }
        if all_tool_calls:
            result["tool_calls_used"] = all_tool_calls
            logger.info(f"Tool calls tracked: {all_tool_calls}")
        return result
