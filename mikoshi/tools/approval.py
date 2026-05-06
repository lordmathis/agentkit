import asyncio
from dataclasses import dataclass
from typing import Any

from mikoshi.tools.context import ToolCallContext


@dataclass
class PendingApproval:
    approval_id: str
    chat_id: str
    tool_name: str
    arguments: dict
    future: asyncio.Future
    context: ToolCallContext


class ToolDeniedError(Exception):
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' was denied by the user")
