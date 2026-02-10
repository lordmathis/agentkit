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
    
    def check_tool_approvals_needed(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """Check if any tool call requires user approval
        
        Args:
            tool_calls: List of tool call objects from LLM response
            
        Returns:
            True if any tool requires approval, False otherwise
        """
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_def = self.tool_manager.get_tool_definition(tool_name)
            if tool_def and tool_def.require_approval:
                logger.info(f"Tool '{tool_name}' requires user approval")
                return True
        return False
    
    def serialize_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Convert tool call object to dict for storage
        
        Args:
            tool_call: Tool call object from LLM response
            
        Returns:
            Serialized tool call with name and arguments
        """
        tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
        
        # Handle both string and dict arguments
        if isinstance(tool_args_str, str):
            tool_args = json.loads(tool_args_str)
        else:
            tool_args = tool_args_str
            
        return {
            "id": tool_call.get("id"),
            "name": tool_call.get("function", {}).get("name", ""),
            "arguments": tool_args
        }

    async def chat(self, messages: List[ChatCompletionMessageParam], additional_tool_servers: Optional[List[str]] = None) -> Dict[str, Any]:
        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                messages = [
                    ChatCompletionDeveloperMessageParam(
                        content=self.system_prompt, role="developer"
                    )
                ] + messages

        # Merge configured tool servers with additional ones from skills
        all_tool_servers = list(self.tool_servers)
        if additional_tool_servers:
            # Add tool servers that aren't already in the list
            for server in additional_tool_servers:
                if server not in all_tool_servers:
                    # Check if the server is actually available
                    available_servers = await self.tool_manager.list_tool_servers()
                    if server in available_servers:
                        all_tool_servers.append(server)
                        logger.info(f"Auto-enabling tool server '{server}' required by skill")
                    else:
                        logger.warning(f"Tool server '{server}' required by skill but not available")

        api_tools = []
        for tool_server in all_tool_servers:

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
            
            # NEW: Check for required approvals BEFORE execution
            if self.check_tool_approvals_needed(message["tool_calls"]):
                return {
                    "pending_approval": True,
                    "tool_calls": [self.serialize_tool_call(tc) for tc in message["tool_calls"]],
                    "assistant_message": message  # Include full message for context
                }

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
