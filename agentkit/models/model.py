from contextlib import AsyncExitStack
import json
from typing import Any, Dict, List, Tuple

from mcp import ClientSession
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from agentkit.config import ProviderConfig
from agentkit.tools import ToolRegistry
from agentkit.tools.mcp import MCPServerTool
from agentkit.tools import AgentKitTool
from agentkit.tools.smolagents import ModelConfig, SmolAgentsTool


class ChatSession:
    """Base model for OpenAI-compatible chat with agent tool calling.
    """

    system_prompt: str = ""

    provider_cfg: ProviderConfig
    model_id: str = ""

    allowed_tools: List[AgentKitTool] = []

    max_iterations: int = 5

    client: OpenAI

    def __init__(
        self,
        system_prompt: str,
        provider_cfg: ProviderConfig,
        model_id: str,
        tool_registry: ToolRegistry,
        allowed_tool_names: List[str] = [],
        max_iterations: int = 5,
    ):
        self.system_prompt = system_prompt
        self.provider = provider_cfg
        self.model_id = model_id
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

        for tool_name, tool in self.tool_registry.get_tools().items():
            if tool_name in allowed_tool_names:
                self.allowed_tools.append(tool)

        self.client = OpenAI(
            api_key=self.provider.api_key, base_url=self.provider.api_base
        )

    async def chat(self, messages: List[ChatCompletionMessageParam]) -> Dict[str, Any]:
        async with AsyncExitStack() as stack:
            if self.system_prompt:
                if not messages or messages[0].get("role") != "system":
                    messages = [
                        ChatCompletionDeveloperMessageParam(
                            content=self.system_prompt, role="developer"
                        )
                    ] + messages

            # Prepare tools for API call
            tools: List[Dict[str, Any]] = []
            sessions: Dict[str, Tuple[ClientSession, AgentKitTool]] = {}
            model_config = ModelConfig(
                api_base=self.provider.api_base,
                api_key=self.provider.api_key,
                model_id=self.model_id,
                model_kwargs={},
            )
            for tool in self.allowed_tools:
                if isinstance(tool, SmolAgentsTool):
                    pass  # TODO:
                elif isinstance(tool, MCPServerTool):
                    session = await stack.enter_async_context(tool.connect(model_config=model_config))
                    raw_tools = await tool.list_tools(session)
                    for t in raw_tools:
                        prefixed_name = f"{tool.server_params.command}_{t['function']['name']}"
                        t["function"]["name"] = prefixed_name
                        tools.append(t)
                        sessions[prefixed_name] = (session, tool)

            # Prepare API call params
            api_params: Dict[str, Any] = {"model": self.model_id, "messages": messages}

            if tools:
                api_params["tools"] = tools

            iteration = 0

            for iteration in range(self.max_iterations):
                print(f"[DEBUG] Chat iteration {iteration + 1}/{self.max_iterations}")

                # Call API
                response = self.client.chat.completions.create(**api_params)
                message = response.choices[0].message

                if not message.tool_calls or len(message.tool_calls) == 0:
                    return response.model_dump()

                print(f"[DEBUG] Processing {len(message.tool_calls)} tool calls")

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

                    if tool_name not in sessions:
                        print(f"[WARNING] No session found for tool '{tool_name}'")
                        continue

                    session, tool = sessions[tool_name]
                    result = await tool.call_tool(session, tool_name.split('_', 1)[1], **tool_args)

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

            return response.model_dump()
