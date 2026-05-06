from dataclasses import dataclass
from typing import Optional

from mikoshi.providers import Provider


@dataclass(frozen=True)
class ToolCallContext:
    provider: Provider
    model_id: str
    chat_id: str
