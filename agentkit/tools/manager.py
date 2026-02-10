import asyncio
import importlib.util
import inspect
import logging
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict

from agentkit.config import MCPConfig
from agentkit.providers import Provider
from agentkit.storage import get_persistent_storage
from agentkit.tools.handler_base import ToolHandler
from agentkit.tools.mcp_handler import MCPToolHandler
from agentkit.tools.toolset_handler import ToolSetHandler
from agentkit.tools.web_tools import WebTools

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, data_dir: str, tools_dir: str, servers: Dict[str, MCPConfig], mcp_timeout: int = 30):
        self._server_map: Dict[str, ToolHandler] = {}  # Server name -> Handler
        self._data_dir = data_dir
        self._tools_dir = tools_dir
        self.mcp_timeout = mcp_timeout
        self.mcp_exit_stack = AsyncExitStack()

        self._mcp_handlers: Dict[str, MCPToolHandler] = {}
        for server_name, config in servers.items():
            mcp_handler = MCPToolHandler(server_name, config, mcp_timeout, self.mcp_exit_stack)
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
    
    def get_persistent_storage(self, tool_server_name):
        return get_persistent_storage(self._data_dir, tool_server_name)

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
            self._server_map[web_tools_handler.server_name] = web_tools_handler
            self._toolset_handlers[web_tools_handler.server_name] = web_tools_handler
            logger.info(f"Successfully initialized built-in WebTools as '{web_tools_handler.server_name}'")
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
                self._toolset_handlers[plugin_instance.server_name] = plugin_instance
                self._server_map[plugin_instance.server_name] = plugin_instance

                logger.info(f"Successfully initialized toolset plugin '{class_name}' as '{plugin_instance.server_name}'")
            except Exception as e:
                logger.error(f"Error initializing toolset plugin '{class_name}': {e}", exc_info=True)

        logger.info("ToolManager initialization completed successfully")

    async def call_tool(self, call_name: str, arguments: dict, provider: Provider, model_id: str) -> Any:
        """Route tool calls to the appropriate handler"""
        try:
            server_name, tool_name = call_name.split("__", 1)
        except ValueError:
            raise ValueError(f"Invalid tool name format: '{call_name}'. Expected 'server__tool'")

        handler = self._server_map.get(server_name)
        if handler is None:
            raise ValueError(f"Tool server '{server_name}' not found")

        result = await handler.call_tool(tool_name, arguments, provider, model_id)
        return result

    
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
    
    def get_tool_definition(self, call_name: str):
        """Get tool definition by full call name (e.g., 'server__tool')
        
        Returns:
            ToolDefinition if found and handler is a ToolSetHandler, None otherwise
        """
        try:
            server_name, tool_name = call_name.split("__", 1)
        except ValueError:
            logger.warning(f"Invalid tool name format: '{call_name}'. Expected 'server__tool'")
            return None
        
        # Only ToolSetHandlers have tool definitions with require_approval
        handler = self._toolset_handlers.get(server_name)
        if handler is None:
            return None
        
        # Access the _tools dictionary directly
        tool_def = handler._tools.get(tool_name)
        return tool_def
    
    async def stop(self):
        """Cleanup all handlers"""
        logger.info("Starting ToolManager cleanup...")
        
        # 1. Cleanup toolset handlers first
        for name, handler in list(self._toolset_handlers.items()):
            try:
                await handler.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of toolset handler '{name}': {e}", exc_info=True)
        
        # 2. Close the exit stack for MCP handlers
        try:
            logger.debug("Closing shared AsyncExitStack for all MCP handlers...")
            await asyncio.wait_for(
                self.mcp_exit_stack.aclose(),
                timeout=self.mcp_timeout
            )
            logger.info("Successfully closed all MCP connections")
        except asyncio.TimeoutError:
            logger.error(f"Timeout closing MCP connections")
        except Exception as e:
            logger.error(f"Error closing MCP connections: {e}", exc_info=True)
        
        # 3. Call cleanup on individual handlers (they just clear their references)
        for server_name, handler in list(self._mcp_handlers.items()):
            try:
                await handler.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of MCP handler '{server_name}': {e}", exc_info=True)
        
        # Clear all references
        self._server_map.clear()
        self._mcp_handlers.clear()
        self._toolset_handlers.clear()
        
        logger.info("ToolManager cleanup completed")