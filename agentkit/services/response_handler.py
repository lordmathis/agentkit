"""Handle LLM responses and message saving."""
import json
import logging
from typing import Any, Dict

from agentkit.db.db import Database

logger = logging.getLogger(__name__)


class ResponseHandler:
    """Handles processing and saving LLM responses."""

    def __init__(self, db: Database):
        self.db = db

    def handle_llm_response(
        self, chat_id: str, response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process LLM response and save assistant message to database.
        
        Args:
            chat_id: The chat ID
            response: The response from the LLM
            
        Returns:
            The original response (for returning to caller)
        """
        logger.info(f"Chat response keys: {response.keys()}")
        logger.info(f"Chat response choices: {response.get('choices', 'NO CHOICES')}")

        if "error" in response:
            error_msg = f"Error: {response['error']}"
            self.db.save_message(
                chat_id, "assistant", error_msg, reasoning_content=None
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

                # Extract tool calls if present
                tool_calls = response.get("tool_calls_used")
                tool_calls_json = json.dumps(tool_calls) if tool_calls else None
                
                logger.info(f"Tool calls from response: {tool_calls}")
                logger.info(f"Tool calls JSON: {tool_calls_json}")

                self.db.save_message(
                    chat_id,
                    "assistant",
                    assistant_content or "",
                    reasoning_content=reasoning_content,
                    tool_calls=tool_calls_json,
                )

        return response
