# agentkit/models/registry.py
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Optional, Type

from agentkit.chatbots import Chatbot
from agentkit.chatbots.plugin import ChatbotPlugin
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class ChatbotRegistry:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_manager: ToolManager,
        chatbots_dir: str,
    ):
        self.provider_registry = provider_registry
        self.tool_manager = tool_manager
        self.chatbots_dir = chatbots_dir
        self._chatbot_classes: Dict[str, Type[ChatbotPlugin]] = {}
        self._register_chatbots()

    def _register_chatbots(self):
        """Discover and register chatbot plugins from the configured directory."""
        chatbots_path = Path(self.chatbots_dir)
        
        if not chatbots_path.exists():
            logger.warning(f"Chatbots directory does not exist: {self.chatbots_dir}")
            return
        
        if not chatbots_path.is_dir():
            logger.warning(f"Chatbots path is not a directory: {self.chatbots_dir}")
            return
        
        # Find all Python files in the chatbots directory
        python_files = list(chatbots_path.glob("*.py"))
        
        for file_path in python_files:
            # Skip __init__.py and private modules
            if file_path.name.startswith("_"):
                continue
            
            try:
                # Load the module dynamically from external plugin directory
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                
                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load spec for module: {file_path}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find all ChatbotPlugin subclasses in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if not issubclass(obj, ChatbotPlugin) or obj is ChatbotPlugin:
                        continue
                    
                    # Register the class itself, not an instance
                    chatbot_name = name.lower()
                    self._chatbot_classes[chatbot_name] = obj
                    logger.info(f"Registered chatbot class: {chatbot_name} from {file_path.name}")
            except Exception as e:
                logger.error(
                    f"Failed to load module from {file_path}: {e}",
                    exc_info=True
                )
        
        logger.info(f"Registered {len(self._chatbot_classes)} chatbot(s)")

    def get_chatbot_class(self, name: str) -> Optional[Type[ChatbotPlugin]]:
        """Retrieve a chatbot class by name."""
        return self._chatbot_classes.get(name)

    def list_chatbots(self) -> list[str]:
        """List all registered chatbot names."""
        return list(self._chatbot_classes.keys())