# agentkit/models/registry.py
from typing import Dict, Optional

from agentkit.chatbots import BaseChatbot
from agentkit.chatbots.assistant import Assistant
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ChatbotRegistry:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_manager: ToolManager,
    ):
        self.provider_registry = provider_registry
        self.tool_manager = tool_manager
        self._models: Dict[str, BaseChatbot] = {}
        self._register_models()

    def _register_models(self):
        assistant = Assistant(
            self.provider_registry,
            self.tool_manager,
        )
        self._models["Assistant"] = assistant

    def get_model(self, name: str) -> Optional[BaseChatbot]:
        """Retrieve a model by name."""
        return self._models.get(name)

    def list_models(self) -> Dict[str, BaseChatbot]:
        """List all registered models."""
        return self._models.copy()