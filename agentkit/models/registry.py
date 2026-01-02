# agentkit/models/registry.py
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, Optional

from agentkit.agents import AgentRegistry
from agentkit.mcps import MCPManager
from agentkit.models import BaseModel
from agentkit.providers import ProviderRegistry


class ModelRegistry:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        agent_registry: AgentRegistry,
        mcp_manager: MCPManager
    ):
        self.provider_registry = provider_registry
        self.agent_registry = agent_registry
        self.mcp_manager = mcp_manager
        self._models: Dict[str, BaseModel] = {}
        self._discover_models()

    def _discover_models(self):
        """Auto-discover all BaseModel subclasses"""
        models_dir = Path(__file__).parent

        for module_info in pkgutil.iter_modules([str(models_dir)]):
            if module_info.name in ('model', 'registry', '__init__'):
                continue

            module = importlib.import_module(f'agentkit.models.{module_info.name}')

            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a BaseModel subclass (not BaseModel itself)
                if (issubclass(obj, BaseModel) and
                    obj is not BaseModel and
                    obj.__module__ == module.__name__):

                    try:
                        model_instance = obj(
                            provider_registry=self.provider_registry,
                            agent_registry=self.agent_registry,
                            mcp_manager=self.mcp_manager
                        )
                        # Use the class name (without "Model" suffix if present) as the registration name
                        model_id = name.lower()
                        if model_id.endswith('model'):
                            model_id = model_id[:-5]
                        self._models[model_id] = model_instance
                        print(f"✓ Registered model: {model_id} ({name})")
                    except Exception as e:
                        print(f"✗ Failed to register model {name}: {e}")

    def get_model(self, name: str) -> Optional[BaseModel]:
        """Retrieve a model by name."""
        return self._models.get(name)

    def list_models(self) -> Dict[str, BaseModel]:
        """List all registered models."""
        return self._models.copy()