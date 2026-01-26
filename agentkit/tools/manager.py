from typing import Dict
import logging
import importlib.util
import inspect
from pathlib import Path

from agentkit.config import MCPConfig
from agentkit.tools.handler_base import ToolHandler
from agentkit.tools.mcp_handler import MCPToolHandler
from agentkit.tools.toolset_handler import ToolSetHandler
from agentkit.tools.web_tools import WebTools

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, tools_dir: str, servers: Dict[str, MCPConfig], mcp_timeout: int = 30):
        self._server_map: Dict[str, ToolHandler] = {}  # Server name -> Handler
        self._tools_dir = tools_dir

        self._mcp_handlers: Dict[str, MCPToolHandler] = {}
        for server_name, config in servers.items():
            mcp_handler = MCPToolHandler(server_name, config, mcp_timeout)
            self._mcp_handlers[server_name] = mcp_handler

        self._toolset_handlers: Dict[str, ToolSetHandler] = {}  # Store discovered toolset handlers

    def _discover_toolset_plugins(self) -> Dict[str, type]:
        """Discover ToolSetHandler subclasses from Python files in tools_dir

        Returns:
            Dict mapping class names to class types
        """
        plugins = {}
        tools_path = Path(self._tools_dir)

        if not tools_path.exists() or not tools_path.is_dir():
            logger.warning(f"Tools directory '{self._tools_dir}' does not exist or is not a directory")
            return plugins

        # Find all Python files in the directory (non-recursive)
        python_files = list(tools_path.glob("*.py"))

        for py_file in python_files:
            # Skip __init__.py and files starting with underscore
            if py_file.name.startswith("_"):
                continue

            try:
                # Load the module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load spec for {py_file}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find ToolSetHandler subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a subclass of ToolSetHandler (but not ToolSetHandler itself)
                    if issubclass(obj, ToolSetHandler) and obj is not ToolSetHandler:
                        # Only include classes defined in this module (not imported ones)
                        if obj.__module__ == module_name:
                            logger.info(f"Discovered toolset plugin: {name} from {py_file.name}")
                            plugins[name] = obj

            except Exception as e:
                logger.error(f"Error loading plugin from {py_file}: {e}", exc_info=True)

        return plugins

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

        # Initialize built-in WebTools
        web_tools_handler = WebTools()
        try:
            web_tools_handler.set_tool_manager(self)
            await web_tools_handler.initialize()
            self._server_map[web_tools_handler.name] = web_tools_handler
            self._toolset_handlers[web_tools_handler.name] = web_tools_handler
            logger.info(f"Successfully initialized built-in WebTools as '{web_tools_handler.name}'")
        except Exception as e:
            logger.error(f"Error initializing WebTools handler: {e}", exc_info=True)

        # Discover and initialize toolset plugins
        plugin_classes = self._discover_toolset_plugins()
        for class_name, plugin_class in plugin_classes.items():
            try:
                # Instantiate the plugin
                plugin_instance = plugin_class()

                # Set tool_manager reference for cross-tool calls
                plugin_instance.set_tool_manager(self)

                await plugin_instance.initialize()

                # Register in both maps
                self._toolset_handlers[plugin_instance.name] = plugin_instance
                self._server_map[plugin_instance.name] = plugin_instance

                logger.info(f"Successfully initialized toolset plugin '{class_name}' as '{plugin_instance.name}'")
            except Exception as e:
                logger.error(f"Error initializing toolset plugin '{class_name}': {e}", exc_info=True)

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
                # Get handler name (could be 'server_name' for MCP or 'name' for toolsets)
                handler_name = getattr(handler, 'server_name', None) or getattr(handler, 'name', 'unknown')
                logger.debug(f"Cleaning up handler '{handler_name}'...")
                await handler.cleanup()
            except Exception as e:
                handler_name = getattr(handler, 'server_name', None) or getattr(handler, 'name', 'unknown')
                logger.error(f"Error during cleanup of handler '{handler_name}': {e}", exc_info=True)

        logger.info("ToolManager cleanup completed")
