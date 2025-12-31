import os

from typing import List, Dict, Optional

import yaml
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    model_ids: Optional[List[str]] = None
    api_key: str
    api_base: str

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000

class MCPConfig(BaseModel):
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}

class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    providers: Dict[str, ProviderConfig] = {}
    mcps: Dict[str, MCPConfig] = {}


def load_config(path: str) -> AppConfig:
    with open(path, 'r') as f:
        content = os.path.expandvars(f.read())
        data = yaml.safe_load(content)

    return AppConfig(**data)
