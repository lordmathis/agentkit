from typing import Any, Dict
from abc import ABC, abstractmethod

from agentkit.providers import ProviderRegistry
from agentkit.mcps import MCPManager


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(
        self, 
        provider_registry: ProviderRegistry,
        mcp_manager: MCPManager
    ):
        self.provider_registry = provider_registry
        self.mcp_manager = mcp_manager
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Override this to set up an agent"""
        pass
    
    @abstractmethod
    def run(self, prompt: str) -> str:
        """Execute the agent with the given prompt"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return the description of what this agent does"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return the JSON schema for the agent's parameters"""
        pass