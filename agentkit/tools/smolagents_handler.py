from typing import Dict, Any
import logging

from smolagents import DuckDuckGoSearchTool, VisitWebpageTool, BaseTool

from agentkit.tools.handler_base import ToolHandler

logger = logging.getLogger(__name__)


class SmolagentsToolHandler(ToolHandler):
    """Handles built-in smolagents tools like web_search"""
    
    def __init__(self):
        self._tools = {}
        self.tool_registry: Dict[str, bool] = {}
        self.server_registry: Dict[str, bool] = {}
    
    async def initialize(self):
        """Initialize built-in smolagents tools"""
        logger.info("Initializing built-in smolagents tools...")
        
        logger.debug("Initializing web_search tool...")
        self._tools['web_search'] = DuckDuckGoSearchTool()
        self.tool_registry['web_search:web_search'] = True
        self.server_registry['web_search'] = True

        logger.debug("Initializing visit_webpage tool...")
        self._tools['visit_webpage'] = VisitWebpageTool()
        self.tool_registry['visit_webpage:visit_webpage'] = True
        self.server_registry['visit_webpage'] = True
        
        logger.info("Built-in smolagents tools initialized successfully")
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a smolagents tool"""
        _, actual_tool_name = tool_name.split(":", 1)
        tool = self._tools.get(actual_tool_name)
        
        if tool is None:
            logger.error(f"SMOLAGENTS tool '{tool_name}' not found in tools dictionary")
            raise ValueError(f"SMOLAGENTS tool '{tool_name}' not found")
        
        logger.debug(f"Calling SMOLAGENTS tool '{tool_name}' with arguments: {arguments}")
        smol_tool: BaseTool = tool
        result = smol_tool(**arguments)
        logger.debug(f"SMOLAGENTS tool '{tool_name}' completed successfully")
        return result
    
    async def list_tools(self, server_name: str) -> list:
        """List available smolagents tools"""
        tool = self._tools.get(server_name)
        if tool is None:
            logger.error(f"SMOLAGENTS tool '{server_name}' not found in tools dictionary")
            raise ValueError(f"SMOLAGENTS tool '{server_name}' not found")
        logger.debug(f"Listing SMOLAGENTS tool: {server_name}")
        return [tool]
    
    async def cleanup(self):
        """Clean up smolagents tools"""
        self._tools.clear()
        self.tool_registry.clear()
        self.server_registry.clear()
