import json
import logging
from typing import Any, Dict, List, Optional

from openai.types.chat import (ChatCompletionDeveloperMessageParam,
                               ChatCompletionMessageParam)

from agentkit.providers.client_base import LLMClient
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

    llm_client: LLMClient

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

        self.llm_client = provider.get_llm_client()

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

        # Track all tool calls made during the conversation
        all_tool_calls = []

        for _ in range(self.max_iterations):
            # Call API using the LLM client abstraction
            response = await self.llm_client.chat_completion(
                model=self.model_id,
                messages=messages,
                tools=api_tools if api_tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            message = response["choices"][0]["message"]

            if not message.get("tool_calls") or len(message.get("tool_calls", [])) == 0:
                # Add tool calls metadata to the response if any were made
                if all_tool_calls:
                    response["tool_calls_used"] = all_tool_calls
                    logger.info(f"Tool calls tracked (success): {all_tool_calls}")
                return response

            # Add assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": message["tool_calls"],
                }
            )

            # Execute tool calls (run agents)
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]
                
                # Handle both string and dict arguments
                if isinstance(tool_args_str, str):
                    tool_args = json.loads(tool_args_str)
                else:
                    tool_args = tool_args_str

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
                        "tool_call_id": tool_call["id"],
                        "content": str(result),
                    }
                )

        # Max iterations reached, add tool calls metadata and return error
        result = {
            "error": "Max iterations reached without final response",
            "messages": messages,
        }
        if all_tool_calls:
            result["tool_calls_used"] = all_tool_calls
            logger.info(f"Tool calls tracked: {all_tool_calls}")
        return result
