from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam
import json
import base64
import logging
import os

from agentkit.chatbots.chatbot import Chatbot
from agentkit.db.db import Database
from agentkit.github.client import GitHubClient

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
        github_client: Optional[GitHubClient] = None,
    ):
        self.chat_id = chat_id
        self.db = db
        self.chatbot = chatbot
        self.github_client = github_client
        self._img_files: List[str] = []
        self._file_contents: Dict[str, str] = {}

    def _parse_content(self, msg_content: str):
        """Parse message content from JSON or return as plain string."""
        try:
            return json.loads(msg_content)
        except (json.JSONDecodeError, TypeError):
            return msg_content

    def _format_attachments(self, attachments: List) -> str:
        """Build text representation of attachments."""
        text = ""
        for attachment in attachments:
            if attachment.content:
                text += f"\n\n--- Content of {attachment.filename} ---\n{attachment.content}"
            elif attachment.content_type.startswith("image/"):
                text += f"\n\n[Image attached: {attachment.filename}]"
        return text

    def _add_to_structured(self, content: List, text: str) -> List:
        """Add text to structured content (list of parts)."""
        if not text:
            return content

        # Find existing text part and append to it
        for part in content:
            if part.get("type") == "text":
                part["text"] += text
                return content

        # No text part found, create one at the beginning
        content.insert(0, {"type": "text", "text": text.strip()})
        return content

    def _process_user_message(self, msg) -> ChatCompletionMessageParam:
        """Process user message with attachments."""
        content = self._parse_content(msg.content)
        attachments = self.db.get_message_attachments(msg.id)

        if not attachments:
            return {"role": "user", "content": content}

        attachment_text = self._format_attachments(attachments)

        if isinstance(content, list):
            content = self._add_to_structured(content, attachment_text)
        else:
            content = content + attachment_text

        return {"role": "user", "content": content}

    def _convert_messages_to_openai_format(
        self, messages: List
    ) -> List[ChatCompletionMessageParam]:
        result: List[ChatCompletionMessageParam] = []

        for msg in messages:
            if msg.role == "user":
                result.append(self._process_user_message(msg))
            elif msg.role == "assistant":
                content = self._parse_content(msg.content)
                result.append({"role": "assistant", "content": content})
            elif msg.role == "system":
                content = self._parse_content(msg.content)
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
    
    async def add_files_from_github(self, repo: str, paths: List[str]) -> List[str]:

        if not self.github_client:
            raise ValueError("GitHub integration is not configured")
        
        file_contents = await self.github_client.fetch_files(repo, paths)
        for path, content in file_contents.items():
            self._file_contents[path] = content
        return list(file_contents.keys())
    
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
        # Save the original user message (without file contents) for display
        saved_message = self.db.save_message(self.chat_id, "user", message)
        
        # Save file attachments to database
        for file_path, file_content in self._file_contents.items():
            filename = os.path.basename(file_path)
            self.db.save_file_attachment(
                message_id=saved_message.id,
                filename=filename,
                file_path=file_path,
                content_type="text/plain",  # Could be enhanced to detect actual content type
                content=file_content
            )
        
        # Save image attachments to database
        for img_path in self._img_files:
            filename = os.path.basename(img_path)
            self.db.save_file_attachment(
                message_id=saved_message.id,
                filename=filename,
                file_path=img_path,
                content_type=f"image/{os.path.splitext(img_path)[1].lower().lstrip('.')}",
                content=None  # Images stored as files, not text content
            )
        
        # Build message content for the chatbot with text files and images
        content_for_chatbot: Union[str, List[Dict[str, Any]]] = message
        
        # Append text file contents to the message for the chatbot
        if self._file_contents:
            for file_path, file_content in self._file_contents.items():
                filename = os.path.basename(file_path)
                content_for_chatbot += f"\n\n--- Content of {filename} ---\n{file_content}"
        
        # If images exist, convert to structured format
        if self._img_files:
            content_parts: List[Dict[str, Any]] = [{"type": "text", "text": content_for_chatbot}]
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
            
            content_for_chatbot = content_parts
        
        # Clear files after using them
        self._img_files.clear()
        self._file_contents.clear()
        
        # Load history and modify the last message (the one we just saved) with file content
        history = self.db.get_chat_history(self.chat_id)
        if history and len(history) > 0:
            # Replace the content of the last message with the version that includes file contents
            last_msg = history[-1]
            if last_msg.role == "user":
                last_msg.content = json.dumps(content_for_chatbot) if isinstance(content_for_chatbot, list) else content_for_chatbot
        
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
