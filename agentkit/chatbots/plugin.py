from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel

from agentkit.chatbots.chatbot import Chatbot
from agentkit.providers.provider import Provider
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ChatbotConfig(BaseModel):
    """Configuration for a chatbot plugin."""
    
    provider: Provider
    model_id: str
    system_prompt: str
    tool_servers: List[str] = []
    max_iterations: int = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True  # Allow Provider type


class ChatbotPlugin(Chatbot, ABC):
    """
    Base class for chatbot plugins.
    
    All plugin chatbots must inherit from this class and implement the configure() method.
    This ensures a consistent initialization signature for automatic discovery.
    """

    def __init__(self, provider_registry: ProviderRegistry, tool_manager: ToolManager):
        """
        Standard initialization for all chatbot plugins.
        
        Args:
            provider_registry: Registry to retrieve provider configurations
            tool_manager: Manager for handling tool/agent interactions
        """
        self.provider_registry = provider_registry
        self.tool_manager = tool_manager
        
        # Let subclasses configure their specific settings
        config = self.configure()
        
        # Initialize the parent Chatbot class
        super().__init__(
            provider=config.provider,
            tool_manager=tool_manager,
            model_id=config.model_id,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            max_iterations=config.max_iterations,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    @abstractmethod
    def configure(self) -> ChatbotConfig:
        """
        Configure the chatbot settings.
        
        Returns:
            ChatbotConfig instance with validated settings
        """
        pass
