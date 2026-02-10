"""Handle automatic chat naming based on conversation history."""
import json
import logging
from typing import List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.chatbots.chatbot import Chatbot

logger = logging.getLogger(__name__)

CHAT_NAMING_SYSTEM_PROMPT = """You are a chat title generator. Your ONLY job is to read a conversation and generate a concise, descriptive title of 3-5 words.

DO NOT answer questions from the conversation.
DO NOT provide explanations.
DO NOT add quotes around the title.

Only output the title itself, nothing else."""

CHAT_NAMING_USER_PROMPT = """Generate a 3-5 word title for this conversation:

{conversation}"""


class ChatNaming:
    """Automatically generates descriptive chat titles from conversation history."""

    def __init__(self, chatbot: Chatbot):
        self.chatbot = chatbot

    async def auto_name_chat(self, history) -> Optional[str]:
        """Generate a chat title based on conversation history.
        
        Args:
            history: List of message objects from the database
            
        Returns:
            Generated title string, or None if generation fails
        """
        if not history or len(history) < 1:
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
                "role": "system",
                "content": CHAT_NAMING_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": CHAT_NAMING_USER_PROMPT.format(conversation=conversation_text),
            }
        ]

        response = await self.chatbot.llm_client.chat_completion(
            model=self.chatbot.model_id,
            messages=naming_messages,
            tools=None,
            temperature=0.2,
            max_tokens=32,
        )
        if "error" in response:
            return None

        choices = response.get("choices", [])
        if choices:
            title = choices[0].get("message", {}).get("content", "").strip()
            if title:
                return title

        return None
