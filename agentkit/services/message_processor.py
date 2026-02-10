"""Handle message format conversion and content parsing."""
import base64
import json
import logging
import os
from typing import Any, Dict, List

from openai.types.chat import ChatCompletionMessageParam

from agentkit.db.db import Database

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes and converts message formats between internal and OpenAI formats."""

    def __init__(self, db: Database):
        self.db = db

    def parse_content(self, msg_content: str):
        """Parse message content from JSON or return as plain string."""
        try:
            return json.loads(msg_content)
        except (json.JSONDecodeError, TypeError):
            return msg_content

    def process_user_message(self, msg) -> ChatCompletionMessageParam:
        """Process user message and reconstruct content with attachments from disk."""
        content = self.parse_content(msg.content)
        attachments = self.db.get_message_attachments(msg.id)
        
        if not attachments:
            return {"role": "user", "content": content}
        
        # Extract text content
        content_text = content if isinstance(content, str) else ""
        if not isinstance(content, str):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    content_text = part.get("text", "")
                    break
        
        # Separate attachments into text files and images
        text_files = []
        image_files = []
        for attachment in attachments:
            if attachment.content_type.startswith("image/"):
                image_files.append(attachment)
            else:
                text_files.append(attachment)
        
        # Add text file contents
        if text_files:
            content_text += "\n\n--- Attached Text Files ---\n"
        for attachment in text_files:
            if not os.path.exists(attachment.file_path):
                continue
                
            try:
                with open(attachment.file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                filename = os.path.basename(attachment.file_path)
                content_text += f"\n\n--- Content of {filename} ---\n{file_content}"
            except Exception as e:
                logger.error(f"Failed to read attachment {attachment.file_path}: {e}")
        
        # If no images, return simple text content
        if not image_files:
            return {"role": "user", "content": content_text}
        
        # Build structured content with images
        content_parts: List[Dict[str, Any]] = [{"type": "text", "text": content_text}]
        
        for attachment in image_files:
            if not os.path.exists(attachment.file_path):
                continue
                
            try:
                with open(attachment.file_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode()
                
                ext = os.path.splitext(attachment.file_path)[1].lower().lstrip('.')
                image_format = 'jpeg' if ext in ('jpg', 'jpeg') else ext or 'jpeg'
                
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_format};base64,{img_data}"}
                })
            except Exception as e:
                logger.error(f"Failed to read image {attachment.file_path}: {e}")
        
        return {"role": "user", "content": content_parts}  # type: ignore

    def to_openai_format(
        self, messages: List
    ) -> List[ChatCompletionMessageParam]:
        """Convert internal message format to OpenAI format.
        
        Args:
            messages: List of internal message objects
            
        Returns:
            List of messages in OpenAI format
        """
        result: List[ChatCompletionMessageParam] = []

        for msg in messages:
            if msg.role == "user":
                result.append(self.process_user_message(msg))
            elif msg.role == "assistant":
                content = self.parse_content(msg.content)
                result.append({"role": "assistant", "content": content})
            elif msg.role == "system":
                content = self.parse_content(msg.content)
                result.append({"role": "system", "content": content})

        return result
