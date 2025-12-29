import os

import yaml
from pydantic import BaseModel

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    plugins_dir: str = "plugins"

class MCPConfig(BaseModel):
    command: str
    args: list[str] = []
    env: dict[str, str] = {}

class AppConfig(BaseModel):
    server: ServerConfig
    mcps: dict[str, MCPConfig] = {}


def load_config(path: str) -> AppConfig:
    with open(path, 'r') as f:
        content = os.path.expandvars(f.read())
        data = yaml.safe_load(content)

    return AppConfig(**data)
