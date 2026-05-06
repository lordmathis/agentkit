from dataclasses import dataclass
from typing import Optional

from mikoshi.providers import Provider


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_id: str
    data_dir: str
    connector: str | None
    git_user_name: str
    git_user_email: str


@dataclass(frozen=True)
class ToolCallContext:
    provider: Provider
    model_id: str
    chat_id: str
    workspace: Optional[WorkspaceContext] = None
