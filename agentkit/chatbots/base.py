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

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatCompletionMessageParam],
        *,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...
