import json
from typing import Any, Dict, List

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from agentkit.providers.provider import Provider
from agentkit.tools.manager import ToolManager

class Chatbot:
    """Base model for OpenAI-compatible chat with agent tool calling."""

    system_prompt: str = ""

    provider: Provider
    model_id: str = ""

    max_iterations: int = 5
    temperature: float = 0.7
    max_tokens: int = 2000

    client: OpenAI

    def __init__(
        self,
        provider: Provider,
        tool_manager: ToolManager,
        model_id: str = "",
        system_prompt: str = "",
        tool_servers: List[str] = [],
        max_iterations: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        self.system_prompt = system_prompt
        self.provider = provider
        self.model_id = model_id
        self.tool_manager = tool_manager
        self.tool_servers = tool_servers
        self.max_iterations = max_iterations
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
                # Handle different tool types (MCP uses 'parameters', smolagents uses 'inputs')
                if hasattr(tool, 'parameters'):
                    parameters = tool.parameters
                elif hasattr(tool, 'inputs'):
                    parameters = tool.inputs
                else:
                    parameters = {}
                
                api_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"{tool_server}:{tool.name}",
                            "description": tool.description,
                            "parameters": parameters,
                        }
                    }
                )

        # Prepare API call params
        api_params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
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
                    self.provider, self.model_id, tool_name, tool_args
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
