from typing import Dict, Any
import logging
import importlib.util
import inspect
from pathlib import Path

from agentkit.tools.handler_base import ToolHandler

logger = logging.getLogger(__name__)


class AgentPluginHandler(ToolHandler):
    """Handles agent plugins loaded from the agents directory"""
    
    def __init__(self, agents_dir: str, tool_manager):
        self._agents_dir = agents_dir
        self._tool_manager = tool_manager  # Needed for agents to access tools
        self._agents = {}
        self.tool_registry: Dict[str, bool] = {}
        self.server_registry: Dict[str, bool] = {}
    
    async def initialize(self):
        """Discover and load agent plugins from agents_dir"""
        from agentkit.tools.smolagents import SmolAgentPlugin
        
        logger.info("Discovering agent plugins...")
        
        agents_path = Path(self._agents_dir)
        if not agents_path.exists() or not agents_path.is_dir():
            logger.info(f"Agents directory not found: {self._agents_dir}")
            return
        
        for file_path in agents_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                if not spec or not spec.loader:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, SmolAgentPlugin) and obj is not SmolAgentPlugin:
                        agent = obj(self._tool_manager)
                        agent.initialize()
                        self._agents[agent.name] = agent
                        self.tool_registry[f'{agent.name}:{agent.name}'] = True
                        self.server_registry[agent.name] = True
                        logger.info(f"Loaded agent: {agent.name}")
            except Exception as e:
                logger.error(f"Failed to load agent from {file_path}: {e}", exc_info=True)
        
        logger.info(f"Agent plugin discovery completed, loaded {len(self._agents)} agents")
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute an agent plugin"""
        _, agent_name = tool_name.split(":", 1)
        agent = self._agents.get(agent_name)
        
        if agent is None:
            logger.error(f"SMOLAGENTS agent '{tool_name}' not found in agents dictionary")
            raise ValueError(f"SMOLAGENTS agent '{tool_name}' not found")
        
        logger.debug(f"Calling SMOLAGENTS agent '{tool_name}' with arguments: {arguments}")
        # Note: agents need provider and model_id from the call context
        # This will need to be passed through from ToolManager.call_tool
        result = agent.run(**arguments)
        logger.debug(f"SMOLAGENTS agent '{tool_name}' completed successfully")
        return result
    
    async def list_tools(self, server_name: str) -> list:
        """List available tools for an agent"""
        # TODO: implement listing tools for smolagents agents
        logger.debug(f"Listing tools for SMOLAGENTS agent '{server_name}' (not yet implemented)")
        return []
    
    async def cleanup(self):
        """Clean up all agent plugins"""
        for agent_name, agent in self._agents.items():
            try:
                logger.debug(f"Cleaning up agent '{agent_name}'...")
                agent.cleanup()
                logger.debug(f"Agent '{agent_name}' cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up agent '{agent_name}': {e}", exc_info=True)
        
        self._agents.clear()
        self.tool_registry.clear()
        self.server_registry.clear()
