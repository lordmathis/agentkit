from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam
import json
import base64
import logging
import os

from agentkit.chatbots.chatbot import Chatbot
from agentkit.db.db import Database
from agentkit.github.client import GitHubClient, FileNode

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
        self._github_files: set[str] = set()  # Track which files came from GitHub

    def _parse_content(self, msg_content: str):
        """Parse message content from JSON or return as plain string."""
        try:
            return json.loads(msg_content)
        except (json.JSONDecodeError, TypeError):
            return msg_content

    def _process_user_message(self, msg) -> ChatCompletionMessageParam:
        """Process user message and reconstruct content with attachments from disk."""
        content = self._parse_content(msg.content)
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

    def _to_openai(
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
    
    async def add_files_from_github(
        self, 
        repo: str, 
        paths: List[str], 
        exclude_paths: Optional[List[str]] = None
    ) -> List[str]:
        """Add files from GitHub to chat context.
        
        Args:
            repo: Repository in format "owner/repo"
            paths: List of file or directory paths
            exclude_paths: Optional list of paths to exclude
            
        Returns:
            List of file paths that were added
        """
        if not self.github_client:
            raise ValueError("GitHub integration is not configured")
        
        if exclude_paths is None:
            exclude_paths = []
        
        # Expand directories to get all files
        all_file_paths = await self._expand_paths_to_files(repo, paths, exclude_paths)
        
        # Fetch file contents
        file_contents = await self.github_client.fetch_files(repo, all_file_paths)
        
        uploads_dir = f"uploads/{self.chat_id}"
        os.makedirs(uploads_dir, exist_ok=True)
        
        saved_paths = []
        for github_path, content in file_contents.items():
            # Create a safe filename from the GitHub path
            safe_filename = github_path.replace("/", "_")
            local_path = f"{uploads_dir}/{safe_filename}"
            
            # Write content to disk
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Add to pending context with local path
            self._file_contents[local_path] = content
            self._github_files.add(local_path)  # Track that this is a GitHub file
            saved_paths.append(local_path)
            
        return saved_paths
    
    def remove_github_files(self) -> None:
        """Remove all GitHub files from the pending context."""
        # Remove files that are tracked as GitHub files
        for github_path in list(self._github_files):
            self._file_contents.pop(github_path, None)
            self._img_files = [f for f in self._img_files if f != github_path]
        
        # Clear the tracking set
        self._github_files.clear()
    
    def remove_uploaded_file(self, file_path: str) -> None:
        """Remove a specific uploaded file from the pending context.
        
        Args:
            file_path: The file path to remove (relative to chat uploads directory)
        """
        # Remove from file contents dict
        self._file_contents.pop(file_path, None)
        
        # Remove from image files list
        if file_path in self._img_files:
            self._img_files.remove(file_path)
    
    async def _expand_paths_to_files(
        self, 
        repo: str, 
        paths: List[str], 
        exclude_paths: List[str]
    ) -> List[str]:
        """Expand paths (which may include directories) to a list of file paths.
        
        Args:
            repo: Repository in format "owner/repo"
            paths: List of file or directory paths
            exclude_paths: List of paths to exclude
            
        Returns:
            List of file paths only (directories expanded)
        """
        if not self.github_client:
            raise ValueError("GitHub client is not configured")
            
        exclude_set = set(exclude_paths)
        all_files = []
        
        for path in paths:
            if path in exclude_set:
                continue
                
            # Check if this is a file or directory
            try:
                tree_node = await self.github_client.browse_tree(repo, path)
                
                if tree_node.type == "file":
                    all_files.append(path)
                else:
                    # It's a directory, recursively get all files
                    files_in_dir = await self._get_all_files_in_dir(repo, tree_node, exclude_set)
                    all_files.extend(files_in_dir)
            except Exception as e:
                logger.error(f"Failed to process path {path}: {e}")
                continue
        
        return all_files
    
    async def _get_all_files_in_dir(
        self, 
        repo: str, 
        node: FileNode, 
        exclude_set: set
    ) -> List[str]:
        """Recursively get all file paths in a directory.
        
        Args:
            repo: Repository in format "owner/repo"
            node: Directory node to traverse
            exclude_set: Set of paths to exclude
            
        Returns:
            List of file paths in the directory
        """
        if not self.github_client:
            raise ValueError("GitHub client is not configured")
            
        files = []
        
        if not node.children:
            return files
        
        for child in node.children:
            if child.path in exclude_set:
                continue
                
            if child.type == "file":
                files.append(child.path)
            else:
                # It's a subdirectory, load and recurse
                try:
                    subtree = await self.github_client.browse_tree(repo, child.path)
                    subfiles = await self._get_all_files_in_dir(repo, subtree, exclude_set)
                    files.extend(subfiles)
                except Exception as e:
                    logger.error(f"Failed to process subdirectory {child.path}: {e}")
                    continue
        
        return files
    
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
        # Save the user's text message (WITHOUT file contents)
        saved_message = self.db.save_message(self.chat_id, "user", message)
        
        # Save file attachments metadata to database (files are already on disk)
        for file_path in self._file_contents.keys():
            filename = os.path.basename(file_path)
            self.db.save_file_attachment(
                message_id=saved_message.id,
                filename=filename,
                file_path=file_path,
                content_type="text/plain"  # Could be enhanced to detect actual content type
            )
        
        # Save image attachments metadata to database
        for img_path in self._img_files:
            filename = os.path.basename(img_path)
            self.db.save_file_attachment(
                message_id=saved_message.id,
                filename=filename,
                file_path=img_path,
                content_type=f"image/{os.path.splitext(img_path)[1].lower().lstrip('.')}"
            )
        
        # Clear files after saving metadata
        self._img_files.clear()
        self._file_contents.clear()
        self._github_files.clear()  # Clear GitHub file tracking
        
        # Load history (will reconstruct messages with attachments from disk)
        history = self.db.get_chat_history(self.chat_id)
        chat = self.db.get_chat(self.chat_id)
        messages = self._to_openai(history)
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
