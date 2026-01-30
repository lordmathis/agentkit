from abc import ABC, abstractmethod
from typing import Any

from agentkit.providers import Provider


class ToolHandler(ABC):
    """Base handler for a type of tool"""
    server_name: str
    
    @abstractmethod
    async def initialize(self) -> None:
        """Set up the handler and register its tools"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict, provider: Provider, model_id: str) -> Any:
        """Execute a tool"""
        pass
    
    @abstractmethod
    async def list_tools(self) -> list:
        """List available tools"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources"""
        pass
