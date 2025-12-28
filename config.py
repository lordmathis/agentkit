import os

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    command: str
    args: list[str] = []
    env: dict[str, str] = {}

class Config(BaseModel):
    servers: dict[str, ServerConfig] = {}


def load_config(path: str) -> Config:
    with open(path, 'r') as f:
        content = os.path.expandvars(f.read())
        data = yaml.safe_load(content)

    return Config(**data)
