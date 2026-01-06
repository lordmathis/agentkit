import json
from typing import Any, Dict, List

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from agentkit.config import ProviderConfig
from agentkit.tools.manager import ToolManager


class ChatSession:
    """Base model for OpenAI-compatible chat with agent tool calling.
    """

    system_prompt: str = ""

    provider_cfg: ProviderConfig
    model_id: str = ""


    max_iterations: int = 5

    client: OpenAI

    def __init__(
        self,
        system_prompt: str,
        provider_cfg: ProviderConfig,
        model_id: str,
        tool_manager: ToolManager,
        tool_servers: List[str] = [],
        max_iterations: int = 5,
    ):
        self.system_prompt = system_prompt
        self.provider = provider_cfg
        self.model_id = model_id
        self.tool_manager = tool_manager
        self.tool_servers = tool_servers
        self.max_iterations = max_iterations

        self.client = OpenAI(
            api_key=self.provider.api_key, base_url=self.provider.api_base
        )

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
                api_tools.append(
                    {
                        "name": f"{tool_server}:{tool.name}",
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                )

        # Prepare API call params
        api_params: Dict[str, Any] = {"model": self.model_id, "messages": messages}
        if api_tools:
            api_params["tools"] = api_tools

        for _ in range(self.max_iterations):
            # Call API
            response = self.client.chat.completions.create(**api_params)
            message = response.choices[0].message

            if not message.tool_calls or len(message.tool_calls) == 0:
                return response.model_dump()

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

                result = await self.tool_manager.call_tool(
                    self.provider_cfg, self.model_id, tool_name, tool_args
                )

                # Add tool result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

                api_params["messages"] = messages

            # Get response after tool execution
            response = self.client.chat.completions.create(**api_params)

        # Max iterations reached, return error
        return {
            "error": "Max iterations reached without final response",
            "messages": messages,
        }