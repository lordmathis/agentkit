from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ModelConfig:
    api_base: str
    api_key: str
    model_id: str
    model_kwargs: dict

@dataclass
class ToolSourceType:
    SINGLE = "single"
    MCP = "mcp"

@dataclass
class ToolSource:
    id: str
    name: str
    description: str
    type: ToolSourceType


class Tool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, description: str, parameters: dict):
        self._name = name
        self._description = description
        self._parameters = parameters

    def get_description(self) -> str:
        return self._description
    
    def get_parameters(self) -> dict:
        """Return the JSON schema for the tool's parameters"""
        return self._parameters
    
    @abstractmethod
    def execute(self, model_cfg: ModelConfig, **kwargs) -> str:
        """Execute the tool with the given parameters"""
        pass