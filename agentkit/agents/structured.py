import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletionMessageParam

from agentkit.agents.base import BaseAgent
from agentkit.agents.streaming import STREAM_DONE, StreamEvent
from agentkit.db.db import Database
from agentkit.db.models import Message
from agentkit.providers.provider import Provider
from agentkit.skills.registry import SkillRegistry
from agentkit.tools.approval import ToolDeniedError
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)

STRUCTURED_SYSTEM_SUFFIX = (
    "\n\nYou are a state transition function. Your memory is the provided CURRENT STATE. "
    "When you have finished calling any tools and are ready to respond to the user, "
    "your final response MUST be a single valid JSON object with exactly two keys: "
    '"user_message" (a string to send to the user) and "new_state" (an object '
    "representing the updated state). If you call tools, wait for results before "
    "finalizing the NEW STATE. Do NOT include any text outside the JSON object."
)


class StructuredAgent(BaseAgent):
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
        max_iterations: int = 5,
    ):
        super().__init__(
            chat_id=chat_id,
            db=db,
            provider=provider,
            tool_manager=tool_manager,
            model_id=model_id,
            system_prompt=system_prompt,
            tool_servers=tool_servers,
            skill_registry=skill_registry,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.max_iterations = max_iterations

    def _build_structured_context(
        self, message: str
    ) -> List[ChatCompletionMessageParam]:
        state = self.db.get_chat_state(self.chat_id)
        system_content = (self.system_prompt or "") + STRUCTURED_SYSTEM_SUFFIX
        system_content += f"\n\nCURRENT STATE: {json.dumps(state)}"

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message},
        ]
        return messages

    async def _loop(
        self, message: str, queue: Optional[asyncio.Queue] = None
    ) -> Dict[str, Any]:
        messages = self._build_structured_context(message)
        tools = await self._get_tools(self.tool_servers)

        try:
            for _ in range(self.max_iterations):
                response = await self._llm(messages, tools if tools else None)
                message_data = response["choices"][0]["message"]

                if (
                    not message_data.get("tool_calls")
                    or len(message_data.get("tool_calls", [])) == 0
                ):
                    user_msg, new_state = self._parse_final_response(
                        message_data.get("content", "")
                    )
                    merged_state = {**self.db.get_chat_state(self.chat_id), **new_state}
                    self.db.update_chat_state(self.chat_id, merged_state)

                    msg = await self._save_message("assistant", user_msg)
                    await self._emit(
                        queue,
                        StreamEvent(type="message", data=self._format_message(msg)),
                    )
                    await self._emit(queue, STREAM_DONE)
                    return {"user_message": user_msg, "new_state": merged_state}

                tool_calls_raw = message_data["tool_calls"]
                messages.append(
                    {
                        "role": "assistant",
                        "content": message_data.get("content"),
                        "tool_calls": tool_calls_raw,
                    }
                )

                for tool_call in tool_calls_raw:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    if isinstance(tool_args_str, str):
                        tool_args = json.loads(tool_args_str)
                    else:
                        tool_args = tool_args_str

                    logger.debug(f"Calling tool: {tool_name}")

                    try:
                        result = await self.tool_manager.call_tool(
                            tool_name,
                            tool_args,
                            self.provider,
                            self.model_id,
                            self.chat_id,
                        )
                    except ToolDeniedError as e:
                        result = f"Tool '{e.tool_name}' was denied by the user."

                    msg = await self._save_message(
                        "tool", str(result), tool_call_id=tool_call["id"]
                    )
                    await self._emit(
                        queue,
                        StreamEvent(type="message", data=self._format_message(msg)),
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": str(result),
                        }
                    )

            msg = await self._save_message(
                "assistant", {"error": "Max iterations reached without final response"}
            )
            await self._emit(
                queue, StreamEvent(type="message", data=self._format_message(msg))
            )
            await self._emit(queue, STREAM_DONE)
            return {"error": "Max iterations reached without final response"}
        except Exception as e:
            await self._emit(queue, StreamEvent(type="error", data={"message": str(e)}))
            await self._emit(queue, STREAM_DONE)
            if queue is None:
                raise
            logger.error(f"StructuredAgent loop error: {e}")

    def _parse_final_response(self, content: str) -> tuple:
        try:
            parsed = json.loads(content)
            user_msg = parsed.get("user_message", content)
            new_state = parsed.get("new_state", {})
            return user_msg, new_state
        except (json.JSONDecodeError, TypeError):
            return content, {}

    async def chat(self, message: str, file_ids: List[str] = []) -> Dict[str, Any]:
        await self._save_message("user", message, file_ids=file_ids)
        result = await self._loop(message)
        await self._generate_title()
        return result

    async def chat_stream(
        self, message: str, queue: asyncio.Queue, file_ids: List[str] = []
    ) -> None:
        await self._save_message("user", message, file_ids=file_ids)
        await self._loop(message, queue=queue)
        await self._generate_title()

    def _prepare_retry(self) -> Optional[str]:
        history = self.db.get_chat_history(self.chat_id)
        last_assistant = None
        last_user = None
        for msg in reversed(history):
            if msg.role == "assistant" and last_assistant is None:
                last_assistant = msg
            elif msg.role == "user" and last_user is None:
                last_user = msg
            if last_assistant and last_user:
                break

        if not last_user:
            return None

        if last_assistant:
            for msg in history:
                if msg.role == "tool" and msg.sequence > last_assistant.sequence:
                    self.db.delete_message(msg.id)
            self.db.delete_message(last_assistant.id)

        return last_user.content

    async def retry(self) -> Dict[str, Any]:
        message = self._prepare_retry()
        if not message:
            return {"error": "No user message to retry"}
        return await self._loop(message)

    async def retry_stream(self, queue: asyncio.Queue) -> None:
        message = self._prepare_retry()
        if not message:
            await queue.put(
                StreamEvent(type="error", data={"message": "No user message to retry"})
            )
            await queue.put(STREAM_DONE)
            return
        await self._loop(message, queue=queue)

    def _prepare_edit(self) -> Optional[Message]:
        history = self.db.get_chat_history(self.chat_id)
        last_user = None
        last_assistant = None
        for msg in reversed(history):
            if msg.role == "user" and last_user is None:
                last_user = msg
            elif msg.role == "assistant" and last_assistant is None:
                last_assistant = msg
            if last_user and last_assistant:
                break

        if not last_user:
            return None

        if last_assistant:
            for msg in history:
                if msg.sequence > last_user.sequence:
                    self.db.delete_message(msg.id)

        return last_user

    async def edit(self, new_message: str) -> Dict[str, Any]:
        last_user = self._prepare_edit()

        if not last_user:
            return {"error": "No user message to edit"}

        file_ids_str = getattr(last_user, "file_ids", None)
        file_ids = json.loads(file_ids_str) if file_ids_str else []

        self.db.delete_message(last_user.id)
        await self._save_message("user", new_message, file_ids=file_ids)

        return await self._loop(new_message)

    async def edit_stream(self, new_message: str, queue: asyncio.Queue) -> None:
        last_user = self._prepare_edit()

        if not last_user:
            await queue.put(
                StreamEvent(type="error", data={"message": "No user message to edit"})
            )
            await queue.put(STREAM_DONE)
            return

        file_ids_str = getattr(last_user, "file_ids", None)
        file_ids = json.loads(file_ids_str) if file_ids_str else []

        self.db.delete_message(last_user.id)
        await self._save_message("user", new_message, file_ids=file_ids)

        await self._loop(new_message, queue=queue)


class StructuredAgentPlugin(StructuredAgent):
    default: bool = False
    name: str = ""
    provider_id: str = ""
    model_id: str = ""
    system_prompt: str = ""
    tool_servers: List[str] = []
    max_iterations: int = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def post_init(self) -> None:
        pass
