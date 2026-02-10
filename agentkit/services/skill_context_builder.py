"""Handle @mention parsing and skill context building."""
import logging
import re
from typing import List, Optional, Tuple

from openai.types.chat import ChatCompletionMessageParam

from agentkit.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillContextBuilder:
    """Parses @mentions and builds skill context for chat messages."""

    def __init__(self, skill_registry: Optional[SkillRegistry] = None):
        self.skill_registry = skill_registry

    def parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from a message.
        
        Args:
            message: The message text to parse
            
        Returns:
            List of mentioned skill names (without the @ prefix)
        """
        # Match @word patterns (alphanumeric and underscores)
        pattern = r'@([a-zA-Z0-9_]+)'
        mentions = re.findall(pattern, message)
        return mentions

    def build_skill_context(self, skill_names: List[str]) -> Tuple[str, List[str]]:
        """Build context text from mentioned skills and collect required tool servers.
        
        Args:
            skill_names: List of skill names to load
            
        Returns:
            Tuple of (formatted string with skill contents, list of required tool servers)
        """
        if not self.skill_registry or not skill_names:
            return "", []
        
        skill_context_parts = []
        required_tool_servers = []
        
        for skill_name in skill_names:
            skill = self.skill_registry.get_skill(skill_name)
            if skill:
                try:
                    content = skill.read_content()
                    # Include the @mention in the context so LLM understands it
                    skill_context_parts.append(
                        f"\n\n--- Skill @{skill_name} ---\n{content}"
                    )
                    logger.info(f"Loaded skill @{skill_name} for context")
                    
                    # Collect required tool servers
                    tool_servers = skill.get_required_tool_servers()
                    if tool_servers:
                        required_tool_servers.extend(tool_servers)
                        logger.info(f"Skill @{skill_name} requires tool servers: {tool_servers}")
                except Exception as e:
                    logger.error(f"Error loading skill @{skill_name}: {e}")
            else:
                # Skill doesn't exist, just log it (treat as plain text)
                logger.debug(f"Skill @{skill_name} not found, treating as plain text")
        
        context_str = "\n".join(skill_context_parts) if skill_context_parts else ""
        return context_str, required_tool_servers

    def apply_skill_context_to_messages(
        self,
        messages: List[ChatCompletionMessageParam],
        skill_context: str
    ) -> List[ChatCompletionMessageParam]:
        """Apply skill context to message list by augmenting system prompt.
        
        Args:
            messages: List of messages in OpenAI format
            skill_context: The skill context to add
            
        Returns:
            Updated message list with skill context
        """
        if not skill_context:
            return messages
        
        # Find existing system/developer message or prepend a new one
        if messages and messages[0].get("role") in ("system", "developer"):
            # Append skill context to existing system prompt
            existing_content = messages[0].get("content", "")
            if isinstance(existing_content, str):
                messages[0]["content"] = existing_content + skill_context
            else:
                # If content is structured, add as text part
                messages[0]["content"] = str(existing_content) + skill_context
        else:
            # Prepend new system message with skill context
            messages.insert(0, {
                "role": "system",
                "content": skill_context.strip()
            })
        
        return messages
