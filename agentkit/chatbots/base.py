import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.providers.client_base import LLMClient
from agentkit.providers.provider import Provider
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agent types."""

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

    def _check_tool_approvals_needed(self, tool_calls: List[Dict[str, Any]]) -> bool:
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_def = self.tool_manager.get_tool_definition(tool_name)
            if tool_def and tool_def.require_approval:
                logger.info(f"Tool '{tool_name}' requires user approval")
                return True
        return False

    def _serialize_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
        if isinstance(tool_args_str, str):
            tool_args = json.loads(tool_args_str)
        else:
            tool_args = tool_args_str
        return {
            "id": tool_call.get("id"),
            "name": tool_call.get("function", {}).get("name", ""),
            "arguments": tool_args,
        }

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatCompletionMessageParam],
        *,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...
