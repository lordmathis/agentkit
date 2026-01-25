from enum import Enum
import os
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel


class FilterCondition(BaseModel):
    """A single filter condition"""
    field: str  # JSONPath expression to the field (e.g., "id", "architecture", "pricing.prompt")
    contains: Optional[str] = None
    excludes: Optional[str] = None
    equals: Optional[Any] = None
    # Could add more operators: gt, lt, in_list, regex, etc.


class ModelFilter(BaseModel):
    """Filter configuration for dynamically fetching model IDs"""
    conditions: List[FilterCondition] = []
    endpoint: str = "/models"  # Endpoint to append to api_base


class ProviderConfig(BaseModel):
    model_ids: Optional[List[str]] = None
    model_filter: Optional[ModelFilter] = None
    api_key: Optional[str] = None
    api_base: str
    basic_auth_token: Optional[str] = None
    verify_ssl: bool = True

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000

class MCPType(Enum):
    STDIO = "stdio"
    SSE = "sse"

class MCPConfig(BaseModel):
    command: str
    args: List[str] = []
    type: MCPType
    env: Dict[str, str] = {}

class PluginConfig(BaseModel):
    chatbots_dir: str = "chatbots"

class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    providers: Dict[str, ProviderConfig] = {}
    mcps: Dict[str, MCPConfig] = {}
    plugins: PluginConfig = PluginConfig()
    history_db_path: str = "agentkit.db"
    uploads_dir: str = "uploads"
    mcp_timeout: int = 60
    github_token: Optional[str] = None


def load_config(path: str) -> AppConfig:
    with open(path, 'r') as f:
        content = os.path.expandvars(f.read())
        data = yaml.safe_load(content)

    return AppConfig(**data)
