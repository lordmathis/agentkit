import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.agents.context import format_history, generate_title, parse_mentions
from agentkit.agents.context.messages import extract_assistant_content
from agentkit.agents.context.skills import apply_skill_context, build_skill_context
from agentkit.agents.streaming import StreamEvent
from agentkit.db.db import Database
from agentkit.db.models import Message
from agentkit.providers.provider import Provider
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agent types. Provides infrastructure and contract only."""

    def __init__(
        self,
        chat_id: str,
        db: Database,
        provider: Provider,
        tool_manager: ToolManager,
        model_id: str,
        system_prompt: str = "",
        tool_servers: List[str] = [],
        skill_registry: Optional[SkillRegistry] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.chat_id = chat_id
        self.db = db
        self.provider = provider
        self.tool_manager = tool_manager
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.tool_servers = list(tool_servers)
        self.skill_registry = skill_registry
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm_client = provider.get_llm_client()

    @abstractmethod
    async def chat(self, message: str, file_ids: List[str] = []) -> Dict[str, Any]:
        """Main entry point for sending a message."""
        ...

    @abstractmethod
    async def retry(self) -> Dict[str, Any]:
        """Retry the last message by re-processing."""
        ...

    @abstractmethod
    async def edit(self, new_message: str) -> Dict[str, Any]:
        """Edit the last user message and re-process."""
        ...

    @abstractmethod
    async def chat_stream(
        self, message: str, queue: asyncio.Queue, file_ids: List[str] = []
    ) -> None:
        """Stream chat response through queue."""
        ...

    @abstractmethod
    async def retry_stream(self, queue: asyncio.Queue) -> None:
        """Stream retry response through queue."""
        ...

    @abstractmethod
    async def edit_stream(self, new_message: str, queue: asyncio.Queue) -> None:
        """Stream edit response through queue."""
        ...

    @staticmethod
    def _format_message(msg: Message) -> dict:
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "reasoning_content": msg.reasoning_content,
            "tool_calls": json.loads(msg.tool_calls) if msg.tool_calls else None,
            "tool_call_id": msg.tool_call_id,
            "sequence": msg.sequence,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "files": [],  # Files are only on user message so this shoul be fine
        }
    
    @staticmethod
    async def _emit(queue: Optional[asyncio.Queue], event: StreamEvent) -> None:
        if queue is not None:
            await queue.put(event)

    async def _save_message(
        self,
        role: str,
        content_or_response: str | Dict[str, Any],
        file_ids: List[str] = [],
        tool_call_id: Optional[str] = None,
    ) -> Message:
        """Save a message to the database and return the saved Message object."""
        if role == "assistant":
            if isinstance(content_or_response, dict):
                if "error" in content_or_response:
                    return self.db.save_message(
                        self.chat_id,
                        "assistant",
                        f"Error: {content_or_response['error']}",
                    )
                else:
                    content, reasoning, tool_calls = extract_assistant_content(
                        content_or_response
                    )
                    tool_calls_json = json.dumps(tool_calls) if tool_calls else None
                    return self.db.save_message(
                        self.chat_id,
                        "assistant",
                        content,
                        reasoning_content=reasoning,
                        tool_calls=tool_calls_json,
                    )
            else:
                return self.db.save_message(
                    self.chat_id, "assistant", content_or_response
                )
        elif role == "tool":
            return self.db.save_message(
                self.chat_id,
                "tool",
                str(content_or_response),
                tool_call_id=tool_call_id,
            )
        else:
            file_ids_json = json.dumps(file_ids) if file_ids else None
            msg = self.db.save_message(
                self.chat_id, "user", content_or_response, file_ids=file_ids_json
            )
            if file_ids:
                self.db.attach_files(file_ids)
            return msg

    async def _build_context(self, message: str) -> List[ChatCompletionMessageParam]:
        """Build full context from DB history with skill context injected from @mentions."""
        mentioned_skills = parse_mentions(message)
        skill_context, required_tool_servers = build_skill_context(
            mentioned_skills, self.skill_registry
        )

        if required_tool_servers:
            new_servers = [
                s for s in required_tool_servers if s not in self.tool_servers
            ]
            if new_servers:
                self.tool_servers = self.tool_servers + new_servers
                self.db.update_chat(
                    self.chat_id, tool_servers=json.dumps(self.tool_servers)
                )
                logger.info(
                    f"Activated skill tool servers for chat {self.chat_id}: {new_servers}"
                )

        messages = format_history(self.db, self.chat_id)
        messages = apply_skill_context(messages, skill_context)

        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                messages.insert(0, {"role": "system", "content": self.system_prompt})

        return messages

    async def _get_tools(self, servers: List[str]) -> List[dict]:
        """Get OpenAI-formatted tool definitions for the given servers."""
        api_tools = []
        for tool_server in servers:
            tools = await self.tool_manager.list_tools(tool_server)
            for tool in tools:
                if hasattr(tool, "parameters"):
                    parameters = tool.parameters
                else:
                    parameters = {}
                api_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"{tool_server}__{tool.name}",
                            "description": tool.description,
                            "parameters": parameters,
                        },
                    }
                )
        return api_tools

    async def _llm(
        self,
        messages: List[ChatCompletionMessageParam],
        tools: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Make a single LLM call and return the raw response dict."""
        return await self._llm_client.chat_completion(
            model=self.model_id,
            messages=messages,
            tools=tools if tools else None,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def _generate_title(self) -> None:
        """Fire title generation as a background task."""
        asyncio.create_task(
            generate_title(self.chat_id, self.db, self._llm_client, self.model_id)
        )
