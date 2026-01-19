from typing import Dict, Any
from contextlib import AsyncExitStack
import logging
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agentkit.config import MCPConfig, MCPType
from agentkit.tools.handler_base import ToolHandler

logger = logging.getLogger(__name__)


class MCPToolHandler(ToolHandler):
    """Handles all MCP server connections and tool calls"""
    
    def __init__(self, servers: Dict[str, MCPConfig], timeout: int):
        self._servers = servers
        self._timeout = timeout
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self.tool_registry: Dict[str, bool] = {}  # tool_name -> True (for lookup)
        self.server_registry: Dict[str, bool] = {}  # server_name -> True
    
    async def initialize(self):
        """Connect to all MCP servers and register their tools"""
        logger.info(f"Starting MCPToolHandler with {len(self._servers)} MCP servers")
        
        for server_name, config in self._servers.items():
            try:
                logger.info(f"Initializing MCP server '{server_name}' (type: {config.type})")
                logger.debug(f"Server '{server_name}' - Command: {config.command}, Args: {config.args}")

                if config.type == MCPType.STDIO:
                    server_params = StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=config.env,
                    )
                else:
                    raise ValueError(f"Unsupported MCP type: {config.type}")

                logger.debug(f"Creating stdio client for '{server_name}'...")
                try:
                    read_stream, write_stream = await asyncio.wait_for(
                        self._exit_stack.enter_async_context(stdio_client(server_params)),
                        timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while connecting to stdio client for '{server_name}' (timeout: {self._timeout}s)")
                    raise TimeoutError(f"Failed to connect to MCP server '{server_name}' within {self._timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to create stdio client for '{server_name}': {e}", exc_info=True)
                    raise

                logger.debug(f"Connected to stdio client for '{server_name}', creating session...")
                try:
                    session = ClientSession(read_stream, write_stream)
                    await asyncio.wait_for(
                        self._exit_stack.enter_async_context(session),
                        timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while entering session context for '{server_name}' (timeout: {self._timeout}s)")
                    raise TimeoutError(f"Failed to enter session context for MCP server '{server_name}' within {self._timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to create or enter session for '{server_name}': {e}", exc_info=True)
                    raise

                logger.debug(f"Initializing session for '{server_name}'...")
                try:
                    await asyncio.wait_for(
                        session.initialize(),
                        timeout=self._timeout
                    )
                    logger.info(f"Session initialized successfully for '{server_name}'")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while initializing session for '{server_name}' (timeout: {self._timeout}s)")
                    raise TimeoutError(f"Failed to initialize MCP server '{server_name}' within {self._timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to initialize session for '{server_name}': {e}", exc_info=True)
                    raise

                self._sessions[server_name] = session
                self.server_registry[server_name] = True

                logger.debug(f"Listing tools for '{server_name}'...")
                try:
                    tools_result = await asyncio.wait_for(
                        session.list_tools(),
                        timeout=self._timeout
                    )
                    for tool in tools_result.tools:
                        logger.debug(f"Found tool in '{server_name}': {tool.name}")
                        self.tool_registry[f"{server_name}:{tool.name}"] = True
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while listing tools for '{server_name}' (timeout: {self._timeout}s)")
                    raise TimeoutError(f"Failed to list tools for MCP server '{server_name}' within {self._timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to list tools for '{server_name}': {e}", exc_info=True)
                    raise

                logger.info(f"Successfully initialized MCP server '{server_name}'")

            except Exception as e:
                logger.error(f"Failed to initialize MCP server '{server_name}': {e}")
                # Continue with other servers instead of failing completely
                continue
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute an MCP tool"""
        server_name, actual_tool_name = tool_name.split(":", 1)
        session = self._sessions.get(server_name)
        
        if session is None:
            logger.error(f"MCP session for server '{server_name}' not found")
            raise ValueError(f"MCP session for server '{server_name}' not found")
        
        logger.debug(f"Calling MCP tool '{actual_tool_name}' on server '{server_name}' with arguments: {arguments}")
        try:
            result = await asyncio.wait_for(
                session.call_tool(actual_tool_name, arguments),
                timeout=self._timeout
            )
            logger.debug(f"MCP tool '{actual_tool_name}' on server '{server_name}' completed successfully")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout while calling MCP tool '{actual_tool_name}' on server '{server_name}' (timeout: {self._timeout}s)")
            raise TimeoutError(f"MCP tool '{actual_tool_name}' on server '{server_name}' timed out after {self._timeout} seconds")
        except Exception as e:
            logger.error(f"Error calling MCP tool '{actual_tool_name}' on server '{server_name}': {e}", exc_info=True)
            raise
    
    async def list_tools(self, server_name: str) -> list:
        """List available tools from a specific MCP server"""
        session = self._sessions.get(server_name)
        if session is None:
            logger.error(f"MCP session for server '{server_name}' not found")
            raise ValueError(f"MCP session for server '{server_name}' not found")
        
        logger.debug(f"Listing tools for MCP server '{server_name}'")
        try:
            tools_result = await asyncio.wait_for(
                session.list_tools(),
                timeout=self._timeout
            )
            logger.debug(f"Found {len(tools_result.tools)} tools for MCP server '{server_name}'")
            return tools_result.tools
        except asyncio.TimeoutError:
            logger.error(f"Timeout while listing tools for MCP server '{server_name}' (timeout: {self._timeout}s)")
            raise TimeoutError(f"Failed to list tools for MCP server '{server_name}' within {self._timeout} seconds")
        except Exception as e:
            logger.error(f"Error listing tools for MCP server '{server_name}': {e}", exc_info=True)
            raise
    
    def get_server_params(self, server_name: str) -> Dict[str, Any]:
        """Get the raw server parameters for a specific MCP server

        This allows other components (like smolagents) to create their own
        sessions to the same MCP server.
        """
        config = self._servers.get(server_name)
        if config is None:
            raise ValueError(f"MCP server '{server_name}' not found in configuration")

        return StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )

    async def cleanup(self):
        """Clean up all MCP connections"""
        logger.debug("Closing AsyncExitStack (cleaning up all MCP sessions)...")
        try:
            await asyncio.wait_for(
                self._exit_stack.aclose(),
                timeout=self._timeout
            )
            logger.info("AsyncExitStack closed successfully")
        except asyncio.TimeoutError:
            logger.error(f"Timeout while closing AsyncExitStack (timeout: {self._timeout}s)")
        except Exception as e:
            logger.error(f"Error during AsyncExitStack cleanup: {e}", exc_info=True)

        self._sessions.clear()
        self.tool_registry.clear()
        self.server_registry.clear()
