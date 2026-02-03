import logging
from typing import Dict, Optional

from agentkit.chatbots.factory import ChatbotFactory
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.db.db import Database
from agentkit.github.client import GitHubClient
from agentkit.providers.registry import ProviderRegistry
from agentkit.services.chat_service import ChatConfig, ChatService
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)

class ChatServiceManager:

    def __init__(
        self,
        db: Database,
        provider_registry: ProviderRegistry,
        chatbot_registry: ChatbotRegistry,
        tool_manager: ToolManager,
        github_client: Optional[GitHubClient] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        self.db = db
        self.provider_registry = provider_registry
        self.chatbot_registry = chatbot_registry
        self.tool_manager = tool_manager
        self.github_client = github_client
        self.skill_registry = skill_registry
        self._chat_services: Dict[str, ChatService] = {}

    def create_service(self, chat_id: str, config: ChatConfig) -> ChatService:
        if chat_id in self._chat_services:
            raise ValueError(f"Chat service for '{chat_id}' already exists")

        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat '{chat_id}' not found")

        model_params = config.model_params
        chatbot = ChatbotFactory.create_chatbot(
            model=config.model,
            provider_registry=self.provider_registry,
            chatbot_registry=self.chatbot_registry,
            tool_manager=self.tool_manager,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            temperature=model_params.temperature if model_params else None,
            max_tokens=model_params.max_tokens if model_params else None,
            max_iterations=model_params.max_iterations if model_params else 5,
        )

        chat_service = ChatService(
            chat_id=chat_id,
            db=self.db,
            chatbot=chatbot,
            github_client=self.github_client,
            skill_registry=self.skill_registry,
        )

        self._chat_services[chat_id] = chat_service

        self.db.save_chat_config(
            chat_id=chat_id,
            model=config.model,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            model_params=config.model_params.model_dump() if config.model_params else {},
        )

        return chat_service

    def get_service(self, chat_id: str) -> ChatService:
        service = self._chat_services.get(chat_id)
        if service:
            return service

        config_dict = self.db.get_chat_config(chat_id)
        if not config_dict:
            raise ValueError(f"Chat '{chat_id}' not found")

        config = ChatConfig(**config_dict)
        return self.create_service(chat_id, config)

    def remove_service(self, chat_id: str) -> None:
        if chat_id in self._chat_services:
            del self._chat_services[chat_id]
