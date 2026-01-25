from typing import Dict
import logging

from agentkit.config import MCPConfig
from agentkit.tools.handler_base import ToolHandler
from agentkit.tools.mcp_handler import MCPToolHandler

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, servers: Dict[str, MCPConfig], mcp_timeout: int = 30):
        self._server_map: Dict[str, ToolHandler] = {}  # Server name -> Handler

        self._mcp_handlers: Dict[str, MCPToolHandler] = {}
        for server_name, config in servers.items():
            mcp_handler = MCPToolHandler(server_name, config, mcp_timeout)
            self._mcp_handlers[server_name] = mcp_handler
    
    async def start(self):
        """Initialize all handlers"""
        logger.info("Starting ToolManager...")
        
        # Initialize MCPs
        for mcp_handler in self._mcp_handlers.values():
            try:
                await mcp_handler.initialize()
                self._server_map[mcp_handler.server_name] = mcp_handler
            except Exception as e:
                logger.error(f"Error initializing MCP handler for server '{mcp_handler.server_name}': {e}", exc_info=True)
        
        logger.info("ToolManager initialization completed successfully")

    async def call_tool(self, call_name: str, arguments: dict):
        """Route tool calls to the appropriate handler"""
        try:
            server_name, tool_name = call_name.split("__", 1)
        except ValueError:
            raise ValueError(f"Invalid tool name format: '{call_name}'. Expected 'server__tool'")
        
        handler = self._server_map.get(server_name)
        if handler is None:
            raise ValueError(f"Tool server '{server_name}' not found")
        
        return await handler.call_tool(tool_name, arguments)

    
    async def list_tools(self, server_name: str) -> list:
        """List available tools from a specific server"""
        if server_name in self._server_map:
            return await self._server_map[server_name].list_tools()
        else:
            logger.error(f"Server '{server_name}' not found in registry")
            raise ValueError(f"Unknown server '{server_name}'")
    
    async def list_tool_servers(self) -> list[str]:
        """List all registered tool servers"""
        return list(self._server_map.keys())
    
    async def stop(self):
        """Cleanup all handlers"""
        logger.info("Starting ToolManager cleanup...")
        for handler in self._server_map.values():
            try:
                logger.debug(f"Cleaning up handler for server '{handler.server_name}'...")
                await handler.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of handler for server '{handler.server_name}': {e}", exc_info=True)

        logger.info("ToolManager cleanup completed")
