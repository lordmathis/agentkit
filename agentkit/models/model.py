from contextlib import AsyncExitStack
import json
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from mcp import ClientSession
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from agentkit.config import ProviderConfig
from agentkit.tools import ToolRegistry
from agentkit.tools.mcp import MCPServerTool
from agentkit.tools.registry import BaseTool, ToolType
from agentkit.tools.smolagents import ModelConfig, SmolAgentsInstance, SmolAgentsTool

class _ToolHandler(NamedTuple):
    session: Optional[ClientSession]
    tool: MCPServerTool | SmolAgentsInstance
    tool_type: ToolType


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
        tool_registry: ToolRegistry,
        tool_ids: List[str] = [],
        max_iterations: int = 5,
    ):
        self.system_prompt = system_prompt
        self.provider = provider_cfg
        self.model_id = model_id
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.allowed_tools: List[Tuple[ToolType, BaseTool]] = []

        for tool_name, tool in self.tool_registry.get_tools().items():
            if tool_name in tool_ids:
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

            model_config = ModelConfig(
                api_base=self.provider.api_base,
                api_key=self.provider.api_key,
                model_id=self.model_id,
                model_kwargs={},
            )

            tool_handlers: Dict[str, _ToolHandler] = {}
            api_tools = []

            for tool_type, tool in self.allowed_tools:
                if tool_type == ToolType.SMOLAGENTS and isinstance(tool, SmolAgentsTool):

                    smol_tool: SmolAgentsTool = tool
                    smol_instance: SmolAgentsInstance = smol_tool.create_instance(model_config=model_config)
                    tool_handlers[tool.name] = _ToolHandler(session=None, tool=smol_instance, tool_type=ToolType.SMOLAGENTS)
                    api_tools.append({
                        "type": "function",
                        "function": {
                            "name": smol_tool.name,
                            "description": smol_tool.description,
                            "parameters": smol_tool.parameters
                        }
                    })

                elif tool_type == ToolType.MCP and isinstance(tool, MCPServerTool):

                    mcp_tool: MCPServerTool = tool
                    session = await stack.enter_async_context(mcp_tool.connect(model_config=model_config))
                    raw_tools = await mcp_tool.list_tools(session)
                    for t in raw_tools:
                        prefixed_name = f"{mcp_tool.server_params.command}_{t['function']['name']}"
                        t["function"]["name"] = prefixed_name
                        api_tools.append(t)
                        tool_handlers[prefixed_name] = _ToolHandler(session=session, tool=mcp_tool, tool_type=ToolType.MCP)

            # Prepare API call params
            api_params: Dict[str, Any] = {"model": self.model_id, "messages": messages}

            if api_tools:
                api_params["tools"] = api_tools

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

                    if tool_name not in tool_handlers:
                        print(f"[WARNING] No handler found for tool '{tool_name}'")
                        continue

                    session, tool, tool_type = tool_handlers[tool_name]
                    if tool_type == ToolType.MCP and session is not None:
                        result = await session.call_tool(tool_name.split('_', 1)[1], **tool_args)
                    elif tool_type == ToolType.SMOLAGENTS and isinstance(tool, SmolAgentsInstance):
                        result = tool.run(**tool_args)

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