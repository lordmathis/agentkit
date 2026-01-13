from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam

from agentkit.chatbots.factory import ChatbotFactory
from agentkit.chatbots.chatbot import Chatbot
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.db.db import Database
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ChatConfig(BaseModel):
    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[Dict[str, Any]] = None


class ChatService:

    def __init__(
        self,
        chat_id: str,
        db: Database,
        chatbot: Chatbot,
    ):
        self.chat_id = chat_id
        self.db = db
        self.chatbot = chatbot

    def _convert_messages_to_openai_format(
        self, messages: List
    ) -> List[ChatCompletionMessageParam]:
        result: List[ChatCompletionMessageParam] = []

        for msg in messages:
            if msg.role == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                result.append({"role": "assistant", "content": msg.content})
            elif msg.role == "system":
                result.append({"role": "system", "content": msg.content})

        return result

    async def send_message(self, message: str) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)
        
        self.db.save_message(self.chat_id, "user", message)
        history = self.db.get_chat_history(self.chat_id)
        messages = self._convert_messages_to_openai_format(history)
        response = await self.chatbot.chat(messages)
        
        logger.info(f"Chat response keys: {response.keys()}")
        logger.info(f"Chat response choices: {response.get('choices', 'NO CHOICES')}")

        if "error" in response:
            error_msg = f"Error: {response['error']}"
            self.db.save_message(self.chat_id, "assistant", error_msg, reasoning_content=None)
            # Format error as OpenAI-style response
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": error_msg
                    }
                }]
            }
        else:
            choices = response.get("choices", [])
            if choices:
                message_data = choices[0].get("message", {})
                # Handle both dict and object types
                if isinstance(message_data, dict):
                    assistant_content = message_data.get("content", "")
                    reasoning_content = message_data.get("reasoning_content", None)
                else:
                    assistant_content = getattr(message_data, "content", "")
                    reasoning_content = getattr(message_data, "reasoning_content", None)
                
                self.db.save_message(
                    self.chat_id, "assistant", assistant_content or "", reasoning_content=reasoning_content
                )

        return response


class ChatServiceManager:

    def __init__(
        self,
        db: Database,
        provider_registry: ProviderRegistry,
        chatbot_registry: ChatbotRegistry,
        tool_manager: ToolManager,
    ):
        self.db = db
        self.provider_registry = provider_registry
        self.chatbot_registry = chatbot_registry
        self.tool_manager = tool_manager
        self._chat_services: Dict[str, ChatService] = {}

    def create_chat_service(
        self, chat_id: str, config: ChatConfig
    ) -> ChatService:
        if chat_id in self._chat_services:
            raise ValueError(f"Chat service for '{chat_id}' already exists")

        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat '{chat_id}' not found")

        model_params = config.model_params or {}
        chatbot = ChatbotFactory.create_chatbot(
            model=config.model,
            provider_registry=self.provider_registry,
            chatbot_registry=self.chatbot_registry,
            tool_manager=self.tool_manager,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            temperature=model_params.get("temperature", 0.7),
            max_tokens=model_params.get("max_tokens", 2000),
            max_iterations=model_params.get("max_iterations", 5),
        )

        chat_service = ChatService(
            chat_id=chat_id,
            db=self.db,
            chatbot=chatbot,
        )

        self._chat_services[chat_id] = chat_service

        self.db.save_chat_config(
            chat_id=chat_id,
            model=config.model,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            model_params=config.model_params or {},
        )

        return chat_service

    def get_or_create_chat_service(self, chat_id: str) -> ChatService:
        service = self._chat_services.get(chat_id)
        if service:
            return service

        config_dict = self.db.get_chat_config(chat_id)
        if not config_dict:
            raise ValueError(f"Chat '{chat_id}' not found")

        config = ChatConfig(**config_dict)
        return self.create_chat_service(chat_id, config)

    def get_chat_service(self, chat_id: str) -> Optional[ChatService]:
        return self._chat_services.get(chat_id)

    def remove_chat_service(self, chat_id: str) -> None:
        if chat_id in self._chat_services:
            del self._chat_services[chat_id]
