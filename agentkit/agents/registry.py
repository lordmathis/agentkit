# agentkit/agents/registry.py
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any, Dict, List

from agentkit.agents.agent import BaseAgent  # Not Protocol anymore
from agentkit.mcps import MCPManager
from agentkit.providers import ProviderRegistry


class AgentRegistry:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        mcp_manager: MCPManager
    ):
        self.provider_registry = provider_registry
        self.mcp_manager = mcp_manager
        self._agents: Dict[str, BaseAgent] = {}
        self._discover_agents()
    
    def _discover_agents(self):
        """Auto-discover all BaseAgent subclasses"""
        agents_dir = Path(__file__).parent
        
        for module_info in pkgutil.iter_modules([str(agents_dir)]):
            if module_info.name in ('agent', 'registry', '__init__'):
                continue
            
            module = importlib.import_module(f'agentkit.agents.{module_info.name}')
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a BaseAgent subclass (not BaseAgent itself)
                if (issubclass(obj, BaseAgent) and 
                    obj is not BaseAgent and 
                    obj.__module__ == module.__name__):
                    
                    try:
                        agent_instance = obj(
                            provider_registry=self.provider_registry,
                            mcp_manager=self.mcp_manager
                        )
                        agent_id = name.lower().replace('agent', '')
                        self._agents[agent_id] = agent_instance
                        print(f"✓ Registered agent: {agent_id} ({name})")
                    except Exception as e:
                        print(f"✗ Failed to register agent {name}: {e}")
    
    def get_agent(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered agents as OpenAI tool definitions."""
        tools = []
        for agent_name, agent in self._agents.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": agent_name,
                        "description": agent.get_description(),
                        "parameters": agent.get_parameters(),
                    },
                }
            )
        return tools