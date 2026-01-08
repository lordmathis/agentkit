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
    """Configuration for a chat request."""

    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[Dict[str, Any]] = None


class ChatService:
    """Service layer for handling chat operations with database persistence.

    Note: This service manages chatbot instances and handles database persistence.
    The chatbot instances maintain conversation state and handle tool calling internally.
    """

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
        # Cache chatbot instances per chat session
        self._chatbot_cache: Dict[str, Chatbot] = {}

    def _get_or_create_chatbot(
        self, chat_id: str, config: ChatConfig
    ) -> Chatbot:
        """Get cached chatbot or create new one for the chat session."""
        # For now, we recreate chatbot each time since config can change
        # In a more sophisticated implementation, we'd cache by config hash
        model_params = config.model_params or {}

        return ChatbotFactory.create_chatbot(
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

    def _convert_messages_to_openai_format(
        self, messages: List
    ) -> List[ChatCompletionMessageParam]:
        """Convert database messages to OpenAI ChatCompletionMessageParam format."""
        result: List[ChatCompletionMessageParam] = []

        for msg in messages:
            # Create properly typed message dict
            if msg.role == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                result.append({"role": "assistant", "content": msg.content})
            elif msg.role == "system":
                result.append({"role": "system", "content": msg.content})
            # Note: tool messages would need tool_call_id which we're not storing yet

        return result

    async def send_message(
        self, chat_id: str, message: str, config: ChatConfig
    ) -> Dict[str, Any]:
        """
        Send a message and get AI response with database persistence.

        Args:
            chat_id: ID of the chat session
            message: User message text
            config: Chat configuration (model, prompts, tools, etc.)

        Returns:
            Dictionary containing user message, assistant message, and any tool messages

        Raises:
            ValueError: If chat_id is invalid or model cannot be found
        """
        # Verify chat exists
        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat '{chat_id}' not found")

        # Save user message to DB
        user_msg = self.db.save_message(chat_id, "user", message)

        # Get chat history from DB (including the user message we just saved)
        history = self.db.get_chat_history(chat_id)

        # Convert history to proper OpenAI format
        messages = self._convert_messages_to_openai_format(history)

        # Get or create chatbot instance
        chatbot = self._get_or_create_chatbot(chat_id, config)

        # Call chatbot with full message history
        # The chatbot handles tool calling and returns the final response
        response = await chatbot.chat(messages)

        # Parse response and save messages to DB
        tool_messages = []
        assistant_message = None

        # Handle the response structure
        if "error" in response:
            # If there was an error, save it as assistant message
            assistant_msg = self.db.save_message(
                chat_id, "assistant", f"Error: {response['error']}"
            )
            assistant_message = {
                "id": assistant_msg.id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "sequence": assistant_msg.sequence,
            }
        else:
            # Extract assistant message from response
            choices = response.get("choices", [])
            if choices:
                assistant_content = choices[0].get("message", {}).get("content", "")
                assistant_msg = self.db.save_message(
                    chat_id, "assistant", assistant_content or ""
                )
                assistant_message = {
                    "id": assistant_msg.id,
                    "role": assistant_msg.role,
                    "content": assistant_msg.content,
                    "sequence": assistant_msg.sequence,
                }

            # TODO: Save tool messages if we want to persist tool calls
            # The chatbot handles tool execution internally, but we could
            # extract and save tool call/result pairs from the response

        # Save chat configuration for future reference
        self.db.save_chat_config(
            chat_id=chat_id,
            model=config.model,
            system_prompt=config.system_prompt,
            tool_servers=config.tool_servers,
            model_params=config.model_params or {},
        )

        return {
            "user_message": {
                "id": user_msg.id,
                "role": user_msg.role,
                "content": user_msg.content,
                "sequence": user_msg.sequence,
            },
            "assistant_message": assistant_message,
            "tool_messages": tool_messages,
        }
