# agentkit/models/registry.py
from typing import Dict, Optional

from agentkit.models import ChatSession
from agentkit.models.assistant import Assistant
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ModelRegistry:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_manager: ToolManager,
    ):
        self.provider_registry = provider_registry
        self.tool_manager = tool_manager
        self._models: Dict[str, ChatSession] = {}
        self._register_models()

    def _register_models(self):
        assistant = Assistant(
            self.provider_registry,
            self.tool_manager,
        )
        self._models["Assistant"] = assistant

    def get_model(self, name: str) -> Optional[ChatSession]:
        """Retrieve a model by name."""
        return self._models.get(name)

    def list_models(self) -> Dict[str, ChatSession]:
        """List all registered models."""
        return self._models.copy()