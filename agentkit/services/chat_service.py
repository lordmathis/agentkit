import logging
from typing import Any, Dict, List, Optional
import json

from pydantic import BaseModel

from agentkit.chatbots.chatbot import Chatbot
from agentkit.db.db import Database
from agentkit.github.client import GitHubClient
from agentkit.services.chat_naming import ChatNaming
from agentkit.services.file_handler import FileHandler
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
        chatbot: Chatbot,
        github_client: Optional[GitHubClient] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        self.chat_id = chat_id
        self.db = db
        self.chatbot = chatbot
        
        # Initialize specialized handlers
        self.file_handler = FileHandler(chat_id, db, github_client)
        self.message_processor = MessageProcessor(db)
        self.response_handler = ResponseHandler(db)
        self.skill_context_builder = SkillContextBuilder(skill_registry)
        self.chat_naming = ChatNaming(chatbot)

    # Delegate file operations to FileHandler
    async def handle_file_upload(self, file_path: str, content_type: str) -> None:
        """Handle a file upload by storing it in the pending context."""
        await self.file_handler.handle_file_upload(file_path, content_type)

    async def add_files_from_github(
        self, 
        repo: str, 
        paths: List[str], 
        exclude_paths: Optional[List[str]] = None
    ) -> List[str]:
        """Add files from GitHub to chat context."""
        return await self.file_handler.add_files_from_github(repo, paths, exclude_paths)

    def remove_github_files(self) -> None:
        """Remove all GitHub files from the pending context."""
        self.file_handler.remove_github_files()

    def remove_uploaded_file(self, file_path: str) -> None:
        """Remove a specific uploaded file from the pending context."""
        self.file_handler.remove_uploaded_file(file_path)

    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a user message and get an assistant response.
        
        Args:
            message: The user message text
            
        Returns:
            The LLM response dictionary
        """
        # Save the user's text message (WITHOUT file contents)
        saved_message = self.db.save_message(self.chat_id, "user", message)
        
        # Save file attachments metadata to database
        self.file_handler.save_attachments_to_db(saved_message.id)
        
        # Clear files after saving metadata
        self.file_handler.clear_pending_files()
        
        # Parse @mentions and load skill context
        mentioned_skills = self.skill_context_builder.parse_mentions(message)
        skill_context, required_tool_servers = self.skill_context_builder.build_skill_context(mentioned_skills)
        
        # Load history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        chat = self.db.get_chat(self.chat_id)
        messages = self.message_processor.to_openai_format(history)
        
        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(messages, skill_context)
        
        # Send to LLM
        response = await self.chatbot.chat(messages, additional_tool_servers=required_tool_servers)
        
        # NEW: Handle pending approval
        if response.get("pending_approval"):
            # Save placeholder assistant message with pending status
            saved_message = self.db.save_message(
                self.chat_id, 
                "assistant", 
                "",  # Empty content, will be filled after approval
                reasoning_content=None
            )
            self.db.update_message_status(saved_message.id, "awaiting_tool_approval")
            
            # Save each tool call as a pending approval
            for tool_call in response["tool_calls"]:
                self.db.create_pending_approval(
                    self.chat_id,
                    saved_message.id,
                    tool_call["name"],
                    json.dumps(tool_call["arguments"])
                )
            
            return {
                "status": "awaiting_tool_approval",
                "message_id": saved_message.id,
                "pending_approvals": response["tool_calls"]
            }
        
        # Handle and save response
        response = self.response_handler.handle_llm_response(self.chat_id, response)

        # Auto-name chat after first assistant response
        if chat and chat.title in (None, "", "Untitled Chat"):
            # Reload history to include the assistant's response we just saved
            updated_history = self.db.get_chat_history(self.chat_id)
            new_title = await self.chat_naming.auto_name_chat(updated_history)
            if new_title:
                self.db.update_chat(self.chat_id, title=new_title)

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
        mentioned_skills = self.skill_context_builder.parse_mentions(user_message_content)
        skill_context, required_tool_servers = self.skill_context_builder.build_skill_context(mentioned_skills)
        
        # Load updated history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        messages = self.message_processor.to_openai_format(history)
        
        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(messages, skill_context)
        
        # Send to LLM
        response = await self.chatbot.chat(messages, additional_tool_servers=required_tool_servers)
        
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
        
        # Delete the last user message and any following assistant response
        self.db.delete_message(last_user_message.id)
        
        # Delete the last assistant message if it exists
        last_assistant_message = self.db.get_last_assistant_message(self.chat_id)
        if last_assistant_message:
            self.db.delete_message(last_assistant_message.id)
        
        # Save the edited user message
        self.db.save_message(self.chat_id, "user", new_message)
        
        # Parse @mentions and load skill context
        mentioned_skills = self.skill_context_builder.parse_mentions(new_message)
        skill_context, required_tool_servers = self.skill_context_builder.build_skill_context(mentioned_skills)
        
        # Get updated history and convert to OpenAI format
        history = self.db.get_chat_history(self.chat_id)
        messages = self.message_processor.to_openai_format(history)
        
        # Apply skill context to messages
        messages = self.skill_context_builder.apply_skill_context_to_messages(messages, skill_context)
        
        # Send to LLM
        response = await self.chatbot.chat(messages, additional_tool_servers=required_tool_servers)
        
        # Handle and save response
        response = self.response_handler.handle_llm_response(self.chat_id, response)
        
        return response
    
    # Tool Approval Methods
    
    async def approve_tool(self, approval_id: str) -> Dict[str, Any]:
        """Approve a specific tool and check if ready to resume
        
        Args:
            approval_id: The ID of the approval to approve
            
        Returns:
            Dict with status and optionally pending_count or response
        """
        approval = self.db.get_approval_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        self.db.update_approval_status(approval_id, "approved")
        
        # Check if all approvals for this message are resolved
        pending = self.db.get_pending_approvals_for_message(approval["message_id"])
        
        if len(pending) > 0:
            return {
                "status": "more_approvals_needed", 
                "pending_count": len(pending)
            }
        
        # All approved - execute and continue
        return await self._resume_with_approved_tools(approval["message_id"])

    async def deny_tool(self, approval_id: str) -> Dict[str, Any]:
        """Deny a tool and abort execution
        
        Args:
            approval_id: The ID of the approval to deny
            
        Returns:
            Dict with status="denied"
        """
        approval = self.db.get_approval_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        self.db.update_approval_status(approval_id, "denied")
        self.db.update_message_status(approval["message_id"], "tool_approval_denied")
        
        # Save error message to user
        self.db.save_message(
            self.chat_id,
            "assistant",
            f"I cannot proceed because the tool '{approval['tool_name']}' was not approved."
        )
        
        return {"status": "denied"}

    async def _resume_with_approved_tools(self, message_id: str) -> Dict[str, Any]:
        """Execute all approved tools and get final LLM response
        
        Args:
            message_id: The message ID that was awaiting approval
            
        Returns:
            The final LLM response after tool execution
        """
        approvals = self.db.get_approved_tools_for_message(message_id)
        
        # Get chat history up to the message awaiting approval
        history = self.db.get_chat_history(self.chat_id)
        messages = self.message_processor.to_openai_format(history)
        
        # Execute each approved tool
        tool_results = []
        for approval in approvals:
            try:
                result = await self.chatbot.tool_manager.call_tool(
                    approval["tool_name"],
                    json.loads(approval["arguments"]),
                    self.chatbot.provider,
                    self.chatbot.model_id
                )
                tool_results.append({
                    "tool_call_id": approval["id"],
                    "name": approval["tool_name"],
                    "content": str(result)
                })
            except Exception as e:
                logger.error(f"Error executing approved tool {approval['tool_name']}: {e}")
                tool_results.append({
                    "tool_call_id": approval["id"],
                    "name": approval["tool_name"],
                    "content": f"Error: {str(e)}"
                })
        
        # Add tool results to messages
        for tool_result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_call_id"],
                "content": tool_result["content"]
            })
        
        # Continue conversation with tool results
        response = await self.chatbot.chat(messages)
        
        # Update message with final response
        if "choices" in response and len(response["choices"]) > 0:
            assistant_content = response["choices"][0].get("message", {}).get("content", "")
            self.db.update_message_content(message_id, assistant_content)
            self.db.update_message_status(message_id, "completed")

        # Auto-name chat after tool-approved response
        chat = self.db.get_chat(self.chat_id)
        if chat and chat.title in (None, "", "Untitled Chat"):
            updated_history = self.db.get_chat_history(self.chat_id)
            new_title = await self.chat_naming.auto_name_chat(updated_history)
            if new_title:
                self.db.update_chat(self.chat_id, title=new_title)
        
        return response
