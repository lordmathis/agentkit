import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Optional, Type

from agentkit.agents.base import BaseAgent
from agentkit.agents.react import ReActAgent, ReActAgentPlugin
from agentkit.agents.structured import StructuredAgentPlugin
from agentkit.db.db import Database
from agentkit.providers.registry import ProviderRegistry
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Discovers and registers agent plugin classes from a directory."""

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_manager: ToolManager,
        agents_dir: str,
    ):
        self.provider_registry = provider_registry
        self.tool_manager = tool_manager
        self.agents_dir = agents_dir
        self._agent_classes: Dict[str, Type[ReActAgentPlugin]] = {}
        self._register_agents()

    def _register_agents(self):
        """Discover and register agent plugins from the configured directory."""
        agents_path = Path(self.agents_dir)

        if not agents_path.exists():
            logger.warning(f"Agents directory does not exist: {self.agents_dir}")
            return

        if not agents_path.is_dir():
            logger.warning(f"Agents path is not a directory: {self.agents_dir}")
            return

        python_files = list(agents_path.glob("*.py"))

        for file_path in python_files:
            if file_path.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)

                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load spec for module: {file_path}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if not issubclass(
                        obj, (ReActAgentPlugin, StructuredAgentPlugin)
                    ) or obj in (ReActAgentPlugin, StructuredAgentPlugin):
                        continue

                    required_attrs = ["provider_id", "model_id"]
                    missing_attrs = []
                    for attr in required_attrs:
                        val = getattr(obj, attr, "")
                        if not val:
                            missing_attrs.append(attr)

                    if missing_attrs:
                        agent_name = obj.name if obj.name else name.lower()
                        logger.warning(
                            f"Plugin '{agent_name}' missing required attributes: {', '.join(missing_attrs)}, skipping"
                        )
                        continue

                    agent_name = obj.name if obj.name else name.lower()
                    self._agent_classes[agent_name] = obj
                    logger.info(
                        f"Registered agent class: {agent_name} from {file_path.name}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to load module from {file_path}: {e}", exc_info=True
                )

        logger.info(f"Registered {len(self._agent_classes)} agent(s)")

    def get_agent_class(self, name: str) -> Optional[Type[ReActAgentPlugin]]:
        """Retrieve an agent class by name."""
        return self._agent_classes.get(name)

    def list_agent_names(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agent_classes.keys())

    def get_default_agent_name(self) -> Optional[str]:
        """Return the name of the first registered agent class with default=True."""
        for name, cls in self._agent_classes.items():
            if getattr(cls, "default", False):
                return name
        return None


class AgentManager:
    """Manages agent instances per chat. Handles instantiation and lifecycle."""

    def __init__(
        self,
        db: Database,
        provider_registry: ProviderRegistry,
        agent_registry: AgentRegistry,
        tool_manager: ToolManager,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        self.db = db
        self.provider_registry = provider_registry
        self.agent_registry = agent_registry
        self.tool_manager = tool_manager
        self.skill_registry = skill_registry
        self._agents: Dict[str, BaseAgent] = {}

    def _resolve_agent_params(
        self,
        config: dict,
        defaults: Optional[Dict] = None,
    ) -> Dict:
        """Extract and resolve agent constructor params from config dict.

        Args:
            config: Configuration dictionary with model, system_prompt, tool_servers, model_params
            defaults: Optional defaults from agent class attributes

        Returns:
            Dict with resolved constructor params
        """
        model_params = config.get("model_params") or {}
        d = defaults or {}

        return {
            "system_prompt": config.get("system_prompt") or d.get("system_prompt", ""),
            "tool_servers": config.get("tool_servers") or d.get("tool_servers", []),
            "temperature": model_params.get("temperature", d.get("temperature")),
            "max_tokens": model_params.get("max_tokens", d.get("max_tokens")),
            "max_iterations": model_params.get(
                "max_iterations", d.get("max_iterations", 5)
            ),
        }

    def _hydrate(self, chat_id: str, config: dict) -> BaseAgent:
        """Instantiate agent from config dict without persisting."""
        model = config.get("model")
        if not model:
            raise ValueError("Model is required")

        if ":" in model:
            provider_name, model_id = model.split(":", 1)
            provider = self.provider_registry.get_provider(provider_name)
            if not provider:
                raise ValueError(f"Provider '{provider_name}' not found")

            params = self._resolve_agent_params(config)
            return ReActAgent(
                chat_id=chat_id,
                db=self.db,
                provider=provider,
                tool_manager=self.tool_manager,
                model_id=model_id,
                skill_registry=self.skill_registry,
                **params,
            )

        agent_class = self.agent_registry.get_agent_class(model)
        if not agent_class:
            raise ValueError(f"Agent '{model}' not found in registry")

        provider = self.provider_registry.get_provider(agent_class.provider_id)
        if not provider:
            raise ValueError(f"Provider '{agent_class.provider_id}' not found")

        defaults = {
            "system_prompt": agent_class.system_prompt,
            "tool_servers": agent_class.tool_servers,
            "temperature": agent_class.temperature,
            "max_tokens": agent_class.max_tokens,
            "max_iterations": agent_class.max_iterations,
        }
        params = self._resolve_agent_params(config, defaults)

        agent = agent_class(
            chat_id=chat_id,
            db=self.db,
            provider=provider,
            tool_manager=self.tool_manager,
            model_id=agent_class.model_id,
            skill_registry=self.skill_registry,
            **params,
        )
        agent.post_init()
        return agent

    def create(self, chat_id: str, config: dict) -> BaseAgent:
        """Create an agent for a chat and persist config to DB."""
        if chat_id in self._agents:
            raise ValueError(f"Agent for chat '{chat_id}' already exists")

        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat '{chat_id}' not found")

        agent = self._hydrate(chat_id, config)
        self._agents[chat_id] = agent

        model = config.get("model")
        system_prompt = config.get("system_prompt")
        tool_servers = config.get("tool_servers") or []
        model_params = config.get("model_params") or {}
        self.db.save_chat_config(
            chat_id=chat_id,
            model=model,
            system_prompt=system_prompt,
            tool_servers=tool_servers,
            model_params=model_params,
        )

        return agent

    def get(self, chat_id: str) -> BaseAgent:
        """Get agent for chat, hydrating from DB config if not in memory."""
        agent = self._agents.get(chat_id)
        if agent:
            return agent

        config_dict = self.db.get_chat_config(chat_id)
        if not config_dict:
            raise ValueError(f"Chat '{chat_id}' not found")

        agent = self._hydrate(chat_id, config_dict)
        self._agents[chat_id] = agent
        return agent

    def remove(self, chat_id: str) -> None:
        """Remove agent from memory."""
        if chat_id in self._agents:
            del self._agents[chat_id]
