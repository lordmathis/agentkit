from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ToolHandler(ABC):
    """Base handler for a type of tool"""
    server_name: str
    
    @abstractmethod
    async def initialize(self) -> None:
        """Set up the handler and register its tools"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
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
