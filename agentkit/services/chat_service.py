import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from pydantic import BaseModel

from agentkit.chatbots.base import BaseAgent
from agentkit.db.db import Database
from agentkit.github.client import GitHubClient
from agentkit.services.chat_naming import ChatNaming
from agentkit.services.message_processor import MessageProcessor
from agentkit.services.response_handler import ResponseHandler
from agentkit.services.skill_context_builder import SkillContextBuilder
from agentkit.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class ModelParams(BaseModel):
    """Model parameters for chatbot configuration."""

    max_iterations: Optional[int] = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatConfig(BaseModel):
    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[ModelParams] = None


class ChatService:
    """Main service for handling chat operations, orchestrating specialized components."""

    def __init__(
        self,
        chat_id: str,
        db: Database,
        chatbot: BaseAgent,
        github_client: Optional[GitHubClient] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        self.chat_id = chat_id
        self.db = db
        self.chatbot = chatbot

        # Initialize specialized handlers
        self.message_processor = MessageProcessor(db)
        self.response_handler = ResponseHandler(db)
        self.skill_context_builder = SkillContextBuilder(skill_registry)
        self.chat_naming = ChatNaming(chatbot)

    def _activate_skill_tool_servers(self, required_servers: List[str]) -> None:
        """Add skill-required tool servers to the chatbot, persisting them like a settings change.

        Once activated, the servers live in self.chatbot.tool_servers and the DB,
        so they are available for all future messages without re-scanning history.
        """
        new_servers = [
            s for s in required_servers if s not in self.chatbot.tool_servers
        ]
        if not new_servers:
            return
        self.chatbot.tool_servers = self.chatbot.tool_servers + new_servers
        self.db.update_chat(
            self.chat_id,
            tool_servers=json.dumps(self.chatbot.tool_servers),
        )
        logger.info(
            f"Activated skill tool servers for chat {self.chat_id}: {new_servers}"
        )

    async def send_message(
        self, message: str, file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send a user message and get an assistant response.

        Args:
            message: The user message text

        Returns:
            The LLM response dictionary
        """
        file_ids = file_ids or []

        # Verify file_ids are pending and exist
        if file_ids:
            pending_files = self.db.list_pending_files()
            pending_file_ids = {f.id for f in pending_files}
            for fid in file_ids:
                if fid not in pending_file_ids:
                    logger.warning(
                        f"File {fid} is either not found or already attached."
                    )

        # Save the user's text message with file_ids
        import json

        file_ids_str = json.dumps(file_ids) if file_ids else None
        self.db.save_message(self.chat_id, "user", message, file_ids=file_ids_str)

        # Mark files as attached
        if file_ids:
            self.db.attach_files(file_ids)

        # Parse @mentions and load skill context
        mentioned_skills = self.skill_context_builder.parse_mentions(message)
        skill_context, required_tool_servers = (
            self.skill_context_builder.build_skill_context(mentioned_skills)
        )

        # Persist any new skill-required tool servers exactly like a settings change
        if required_tool_servers:
            self._activate_skill_tool_servers(required_tool_servers)

        # Load history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        chat = self.db.get_chat(self.chat_id)
        messages = self.message_processor.to_openai_format(history)

        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(
            messages, skill_context
        )

        # Send to LLM (skill tool servers are already in self.chatbot.tool_servers)
        response = await self.chatbot.chat(messages, chat_id=self.chat_id)

        # Handle and save response
        response = self.response_handler.handle_llm_response(self.chat_id, response)

        # Auto-name chat after first assistant response
        if chat and chat.title in (None, "", "Untitled Chat"):
            asyncio.create_task(self._background_name_chat())

        return response

    async def retry_last_message(self) -> Dict[str, Any]:
        """Retry the last message by deleting the last assistant response and re-processing.

        This is useful when the LLM fails or returns an error. It resends all messages
        up to but not including the last assistant response.

        Returns:
            The response from the LLM after retry

        Raises:
            ValueError: If there's no last assistant message to retry
        """
        # Get the last assistant message
        last_assistant_message = self.db.get_last_assistant_message(self.chat_id)
        if not last_assistant_message:
            raise ValueError("No assistant message to retry")

        # Delete the last assistant message (and its attachments)
        self.db.delete_message(last_assistant_message.id)

        # Get the last user message
        history = self.db.get_chat_history(self.chat_id)
        if not history:
            raise ValueError("No message history found")

        # Find the last user message
        last_user_message = None
        for msg in reversed(history):
            if msg.role == "user":
                last_user_message = msg
                break

        if not last_user_message:
            raise ValueError("No user message found to retry with")

        # Extract the user message content
        user_message_content = last_user_message.content

        # Parse @mentions and load skill context
        mentioned_skills = self.skill_context_builder.parse_mentions(
            user_message_content
        )
        skill_context, required_tool_servers = (
            self.skill_context_builder.build_skill_context(mentioned_skills)
        )

        # Persist any new skill-required tool servers exactly like a settings change
        if required_tool_servers:
            self._activate_skill_tool_servers(required_tool_servers)

        # Load updated history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        messages = self.message_processor.to_openai_format(history)

        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(
            messages, skill_context
        )

        # Send to LLM (skill tool servers are already in self.chatbot.tool_servers)
        response = await self.chatbot.chat(messages, chat_id=self.chat_id)

        # Handle and save response
        response = self.response_handler.handle_llm_response(self.chat_id, response)

        return response

    async def edit_last_user_message(self, new_message: str) -> Dict[str, Any]:
        """Edit the last user message and delete the assistant's response, then re-process.

        This allows users to modify their last message and get a new response from the LLM.

        Args:
            new_message: The new user message content

        Returns:
            The response from the LLM after re-processing

        Raises:
            ValueError: If there's no last user message to edit
        """
        # Get the last user message
        history = self.db.get_chat_history(self.chat_id)
        if not history:
            raise ValueError("No message history found")

        # Find the last user message
        last_user_message = None
        for msg in reversed(history):
            if msg.role == "user":
                last_user_message = msg
                break

        if not last_user_message:
            raise ValueError("No user message found to edit")

        # Keep the file_ids from the original message
        file_ids_str = getattr(last_user_message, "file_ids", None)

        # Delete the last user message and any following assistant response
        self.db.delete_message(last_user_message.id)

        # Delete the last assistant message if it exists
        last_assistant_message = self.db.get_last_assistant_message(self.chat_id)
        if last_assistant_message:
            self.db.delete_message(last_assistant_message.id)

        # Save the edited user message with the old file_ids
        self.db.save_message(self.chat_id, "user", new_message, file_ids=file_ids_str)

        # Parse @mentions and load skill context
        mentioned_skills = self.skill_context_builder.parse_mentions(new_message)
        skill_context, required_tool_servers = (
            self.skill_context_builder.build_skill_context(mentioned_skills)
        )

        # Persist any new skill-required tool servers exactly like a settings change
        if required_tool_servers:
            self._activate_skill_tool_servers(required_tool_servers)

        # Get updated history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        messages = self.message_processor.to_openai_format(history)

        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(
            messages, skill_context
        )

        # Send to LLM (skill tool servers are already in self.chatbot.tool_servers)
        response = await self.chatbot.chat(messages, chat_id=self.chat_id)

        # Handle and save response
        response = self.response_handler.handle_llm_response(self.chat_id, response)

        return response

    async def _background_name_chat(self):
        try:
            history = self.db.get_chat_history(self.chat_id)
            new_title = await self.chat_naming.auto_name_chat(history)
            if new_title:
                self.db.update_chat(self.chat_id, title=new_title)
        except Exception as e:
            logger.warning(f"Background chat naming failed for {self.chat_id}: {e}")
