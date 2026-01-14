from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam
import json
import base64
import logging
import os

from agentkit.chatbots.factory import ChatbotFactory
from agentkit.chatbots.chatbot import Chatbot
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.db.db import Database
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class ChatConfig(BaseModel):
    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[Dict[str, Any]] = None


CHAT_NAMING_PROMPT = """
Based on the following conversation, suggest a concise and descriptive title in 3 to 5 words.
Respond only with the title, without any additional text. Below is the conversation:

{conversation}

"""

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
        self._img_files: List[str] = []
        self._file_contents: Dict[str, str] = {}

    def _convert_messages_to_openai_format(
        self, messages: List
    ) -> List[ChatCompletionMessageParam]:
        result: List[ChatCompletionMessageParam] = []

        for msg in messages:
            # Try to parse content as JSON (for structured content with images)
            try:
                content = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                # If it's not JSON, use as plain string
                content = msg.content
            
            if msg.role == "user":
                result.append({"role": "user", "content": content})
            elif msg.role == "assistant":
                result.append({"role": "assistant", "content": content})
            elif msg.role == "system":
                result.append({"role": "system", "content": content})

        return result

    async def _auto_name_chat(self, history) -> Optional[str]:
        if not history or len(history) < 2:
            return None

        # Build conversation snippet (first 2-3 exchanges)
        conversation_text = ""
        for msg in history[:6]:  # Max 3 exchanges
            if msg.role in ["user", "assistant"]:
                # Extract text content (handle both string and structured content)
                try:
                    content = json.loads(msg.content)
                    if isinstance(content, list):
                        # Extract text from structured content
                        text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
                        content_str = " ".join(text_parts)
                    else:
                        content_str = str(content)
                except (json.JSONDecodeError, TypeError):
                    content_str = msg.content
                
                conversation_text += f"{msg.role.capitalize()}: {content_str}\n"

        # Generate title using the chatbot
        naming_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": CHAT_NAMING_PROMPT.format(conversation=conversation_text),
            }
        ]

        response = await self.chatbot.chat(naming_messages)
        if "error" in response:
            return None

        choices = response.get("choices", [])
        if choices:
            title = choices[0].get("message", {}).get("content", "").strip()
            if title:
                return title

        return None
    
    async def handle_file_upload(self, file_path: str, content_type: str) -> None:
        logger.info(f"Handling file upload: {file_path} with content type: {content_type}")

        if content_type.startswith("image/"):
            self._img_files.append(file_path)
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._file_contents[file_path] = content
                logger.info(f"Read content from {file_path}, length: {len(content)} characters")
        except (UnicodeDecodeError, UnicodeError) as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise ValueError(f"Unsupported file encoding for file: {file_path}")

    async def send_message(self, message: str) -> Dict[str, Any]:
        # Build message content with text files and images
        content: Union[str, List[Dict[str, Any]]] = message
        
        # Append text file contents to the message
        if self._file_contents:
            for file_path, file_content in self._file_contents.items():
                filename = os.path.basename(file_path)
                content += f"\n\n--- Content of {filename} ---\n{file_content}"
        
        # If images exist, convert to structured format
        if self._img_files:
            content_parts: List[Dict[str, Any]] = [{"type": "text", "text": content}]
            for img_path in self._img_files:
                try:
                    # Read image and encode to base64
                    with open(img_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    
                    # Detect image format from path
                    ext = os.path.splitext(img_path)[1].lower().lstrip('.')
                    image_format = 'jpeg' if ext in ('jpg', 'jpeg') else ext or 'jpeg'
                    
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{image_format};base64,{img_data}"}
                    })
                    logger.info(f"Added image {img_path} to message")
                except Exception as e:
                    logger.error(f"Failed to encode image {img_path}: {str(e)}")
            
            content = content_parts
        
        # Save message with structured content (as JSON if it's a list)
        content_to_save = json.dumps(content) if isinstance(content, list) else content
        self.db.save_message(self.chat_id, "user", content_to_save)
        
        # Clear files after using them
        self._img_files.clear()
        self._file_contents.clear()
        
        history = self.db.get_chat_history(self.chat_id)
        chat = self.db.get_chat(self.chat_id)
        messages = self._convert_messages_to_openai_format(history)
        response = await self.chatbot.chat(messages)

        if chat and chat.title in (None, "", "Untitled Chat"):
            new_title = await self._auto_name_chat(history)
            if new_title:
                self.db.update_chat(self.chat_id, title=new_title)

        logger.info(f"Chat response keys: {response.keys()}")
        logger.info(f"Chat response choices: {response.get('choices', 'NO CHOICES')}")

        if "error" in response:
            error_msg = f"Error: {response['error']}"
            self.db.save_message(
                self.chat_id, "assistant", error_msg, reasoning_content=None
            )
            # Format error as OpenAI-style response
            return {
                "choices": [{"message": {"role": "assistant", "content": error_msg}}]
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
                    self.chat_id,
                    "assistant",
                    assistant_content or "",
                    reasoning_content=reasoning_content,
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

    def create_chat_service(self, chat_id: str, config: ChatConfig) -> ChatService:
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
