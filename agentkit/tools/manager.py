from typing import Dict
import logging

from agentkit.config import MCPConfig
from agentkit.providers.provider import Provider
from agentkit.tools.handler_base import ToolHandler, ToolType
from agentkit.tools.mcp_handler import MCPToolHandler
from agentkit.tools.smolagents_handler import SmolagentsToolHandler
from agentkit.tools.agent_handler import AgentPluginHandler

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, servers: Dict[str, MCPConfig], mcp_timeout: int = 30, agents_dir: str = "agents"):
        # Create handlers for each tool type
        self._mcp_handler = MCPToolHandler(servers, mcp_timeout)
        self._smol_handler = SmolagentsToolHandler()
        self._agent_handler = AgentPluginHandler(agents_dir, self)
        
        # Keep a simple map: tool_name -> which handler owns it
        self._tool_handlers: Dict[str, ToolHandler] = {}
        
        # For backward compatibility with agents that access internal state
        self._server_registry: Dict[str, ToolType] = {}  # server_name -> handler type
    
    async def start(self):
        """Initialize all handlers"""
        logger.info("Starting ToolManager...")
        
        await self._mcp_handler.initialize()
        await self._smol_handler.initialize()
        await self._agent_handler.initialize()
        
        # Build routing map: tool_name -> handler
        for tool_name in self._mcp_handler.tool_registry:
            self._tool_handlers[tool_name] = self._mcp_handler
        for tool_name in self._smol_handler.tool_registry:
            self._tool_handlers[tool_name] = self._smol_handler
        for tool_name in self._agent_handler.tool_registry:
            self._tool_handlers[tool_name] = self._agent_handler
        
        # Build server registry for backward compatibility
        for server_name in self._mcp_handler.server_registry:
            self._server_registry[server_name] = ToolType.MCP
        for server_name in self._smol_handler.server_registry:
            self._server_registry[server_name] = ToolType.SMOLAGENTS_TOOL
        for server_name in self._agent_handler.server_registry:
            self._server_registry[server_name] = ToolType.SMOLAGENTS_AGENT
        
        logger.info("ToolManager initialization completed successfully")

    async def call_tool(self, provider: Provider, model_id: str, tool_name: str, arguments: dict):
        """Route tool calls to the appropriate handler"""
        try:
            server_name, actual_tool_name = tool_name.split(":", 1)
        except ValueError:
            logger.error(f"Invalid tool name format: '{tool_name}'. Expected 'server:tool'")
            raise ValueError(f"Invalid tool name format: '{tool_name}'. Expected 'server:tool'")
        
        handler = self._tool_handlers.get(tool_name)
        if handler is None:
            logger.error(f"Tool '{tool_name}' not found in registry")
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            # Note: Agents need provider and model_id, but they're passed through arguments
            # This is a limitation of the current design that could be improved
            if handler == self._agent_handler:
                # Agent plugins might need provider and model_id
                # For now, we'll let them handle it through their run() method
                return await handler.call_tool(tool_name, arguments)
            else:
                return await handler.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            raise
    
    async def list_tools(self, server_name: str) -> list:
        """List available tools from a specific server"""
        # Determine which handler owns this server
        if server_name in self._mcp_handler.server_registry:
            return await self._mcp_handler.list_tools(server_name)
        elif server_name in self._smol_handler.server_registry:
            return await self._smol_handler.list_tools(server_name)
        elif server_name in self._agent_handler.server_registry:
            return await self._agent_handler.list_tools(server_name)
        else:
            logger.error(f"Server '{server_name}' not found in registry")
            raise ValueError(f"Unknown server '{server_name}'")
    
    async def list_tool_servers(self) -> list[str]:
        """List all registered tool servers"""
        servers = []
        servers.extend(self._mcp_handler.server_registry.keys())
        servers.extend(self._smol_handler.server_registry.keys())
        servers.extend(self._agent_handler.server_registry.keys())
        logger.debug(f"Listing {len(servers)} registered tool servers")
        return servers
    
    def get_server_type(self, server_name: str) -> ToolType:
        """Get the type of a specific server"""
        server_type = self._server_registry.get(server_name)
        if server_type is None:
            raise ValueError(f"Unknown server '{server_name}'")
        return server_type
    
    async def stop(self):
        """Cleanup all handlers"""
        logger.info("Starting ToolManager cleanup...")
        
        await self._agent_handler.cleanup()
        await self._smol_handler.cleanup()
        await self._mcp_handler.cleanup()
        
        self._tool_handlers.clear()
        self._server_registry.clear()
        
        logger.info("ToolManager cleanup completed")
