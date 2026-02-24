from abc import ABC
from typing import List, Optional

from agentkit.chatbots.chatbot import Chatbot
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ChatbotPlugin(Chatbot, ABC):
    """
    Base class for chatbot plugins.

    Override class attributes to configure the chatbot:

        class MyChatbot(ChatbotPlugin):
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
    max_tokens: Optional[int] = None

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
