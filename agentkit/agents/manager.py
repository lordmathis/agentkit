import logging
from typing import Dict, Optional

from agentkit.agents.base import BaseAgent
from agentkit.agents.react import ReActAgent
from agentkit.agents.registry import ChatbotRegistry
from agentkit.db.db import Database
from agentkit.providers.registry import ProviderRegistry
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class AgentManager:
    """Thin registry mapping chat_id -> agent. No business logic."""

    def __init__(
        self,
        db: Database,
        provider_registry: ProviderRegistry,
        chatbot_registry: ChatbotRegistry,
        tool_manager: ToolManager,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        self.db = db
        self.provider_registry = provider_registry
        self.chatbot_registry = chatbot_registry
        self.tool_manager = tool_manager
        self.skill_registry = skill_registry
        self._agents: Dict[str, BaseAgent] = {}

    def create(self, chat_id: str, config: dict) -> BaseAgent:
        """Create an agent for a chat and persist config to DB."""
        if chat_id in self._agents:
            raise ValueError(f"Agent for chat '{chat_id}' already exists")

        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat '{chat_id}' not found")

        model = config.get("model")
        if not model:
            raise ValueError("Model is required")

        system_prompt = config.get("system_prompt")
        tool_servers = config.get("tool_servers")
        model_params = config.get("model_params") or {}
        temperature = model_params.get("temperature")
        max_tokens = model_params.get("max_tokens")
        max_iterations = model_params.get("max_iterations", 5)

        if ":" in model:
            provider_name, model_id = model.split(":", 1)
            provider = self.provider_registry.get_provider(provider_name)
            if not provider:
                raise ValueError(f"Provider '{provider_name}' not found")
        else:
            chatbot_class = self.chatbot_registry.get_chatbot_class(model)
            if not chatbot_class:
                raise ValueError(f"Chatbot '{model}' not found in registry")
            provider = self.provider_registry.get_provider(chatbot_class.provider_id)
            if not provider:
                raise ValueError(f"Provider '{chatbot_class.provider_id}' not found")
            model_id = chatbot_class.model_id

        agent = ReActAgent(
            chat_id=chat_id,
            db=self.db,
            provider=provider,
            tool_manager=self.tool_manager,
            model_id=model_id,
            system_prompt=system_prompt or "",
            tool_servers=tool_servers or [],
            skill_registry=self.skill_registry,
            temperature=temperature,
            max_tokens=max_tokens,
            max_iterations=max_iterations,
        )

        self._agents[chat_id] = agent

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

        return self.create(chat_id, config_dict)

    def remove(self, chat_id: str) -> None:
        """Remove agent from memory."""
        if chat_id in self._agents:
            del self._agents[chat_id]
