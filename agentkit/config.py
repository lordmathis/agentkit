from enum import Enum
import os
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    model_ids: Optional[List[str]] = None
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
    agents_dir: str = "agents"

class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    providers: Dict[str, ProviderConfig] = {}
    mcps: Dict[str, MCPConfig] = {}
    plugins: PluginConfig = PluginConfig()
    history_db_path: str = "agentkit.db"
    mcp_timeout: int = 60


def load_config(path: str) -> AppConfig:
    with open(path, 'r') as f:
        content = os.path.expandvars(f.read())
        data = yaml.safe_load(content)

    return AppConfig(**data)
