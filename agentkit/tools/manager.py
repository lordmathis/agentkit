from enum import Enum
from typing import Dict
from contextlib import AsyncExitStack
import logging
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from smolagents import DuckDuckGoSearchTool, VisitWebpageTool, MCPClient

from agentkit.config import MCPConfig, MCPType
from agentkit.providers.provider import Provider

logger = logging.getLogger(__name__)

class ToolType(Enum):
    MCP = "mcp"
    SMOLAGENTS_TOOL = "smolagents_tool"
    SMOLAGENTS_AGENT = "smolagents_agent"

class ToolManager:
    def __init__(self, servers: Dict[str, MCPConfig], mcp_timeout: int = 30):
        self._mcp_servers = servers
        self._sessions = {}  # server_name -> ClientSession
        self._exit_stack = AsyncExitStack()  # Manages all context managers
        self._smol_tools = {}
        self._smol_agents = {}
        self._mcp_client: MCPClient
        self._server_params: Dict[str, StdioServerParameters] = {}
        self._mcp_timeout = mcp_timeout  # Timeout in seconds for MCP operations

        self._server_registry: Dict[str, ToolType] = {}  # server_name -> type of server
        self._tool_registry: Dict[str, ToolType] = {}  # (server_name:tool_name) -> type of tool
        
    async def start(self):
        """Initialize all MCP servers once"""
        logger.info(f"Starting ToolManager with {len(self._mcp_servers)} MCP servers")
        from agentkit.tools.notes_agent import NotesAgent

        for server_name, config in self._mcp_servers.items():
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
                    # Use AsyncExitStack to properly manage context managers with timeout
                    read_stream, write_stream = await asyncio.wait_for(
                        self._exit_stack.enter_async_context(stdio_client(server_params)),
                        timeout=self._mcp_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while connecting to stdio client for '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"Failed to connect to MCP server '{server_name}' within {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to create stdio client for '{server_name}': {e}", exc_info=True)
                    raise

                logger.debug(f"Connected to stdio client for '{server_name}', creating session...")
                try:
                    session = ClientSession(read_stream, write_stream)

                    # Enter session context via exit stack with timeout
                    await asyncio.wait_for(
                        self._exit_stack.enter_async_context(session),
                        timeout=self._mcp_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while entering session context for '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"Failed to enter session context for MCP server '{server_name}' within {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to create or enter session for '{server_name}': {e}", exc_info=True)
                    raise

                logger.debug(f"Initializing session for '{server_name}'...")
                try:
                    await asyncio.wait_for(
                        session.initialize(),
                        timeout=self._mcp_timeout
                    )
                    logger.info(f"Session initialized successfully for '{server_name}'")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while initializing session for '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"Failed to initialize MCP server '{server_name}' within {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to initialize session for '{server_name}': {e}", exc_info=True)
                    raise

                self._sessions[server_name] = session
                self._server_registry[server_name] = ToolType.MCP

                logger.debug(f"Listing tools for '{server_name}'...")
                try:
                    tools = await asyncio.wait_for(
                        session.list_tools(),
                        timeout=self._mcp_timeout
                    )
                    for tool, _ in tools:
                        logger.debug(f"Found tool in '{server_name}': {tool}")
                        self._tool_registry[f"{server_name}:{tool}"] = ToolType.MCP
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while listing tools for '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"Failed to list tools for MCP server '{server_name}' within {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Failed to list tools for '{server_name}': {e}", exc_info=True)
                    raise

                if config.type == MCPType.STDIO:
                    self._server_params[server_name] = StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=config.env,
                    )
                logger.info(f"Successfully initialized MCP server '{server_name}'")

            except Exception as e:
                logger.error(f"Failed to initialize MCP server '{server_name}': {e}")
                # Continue with other servers instead of failing completely
                continue

        logger.info("Initializing built-in tools and agents...")
        try:
            logger.debug("Initializing web_search tool...")
            self._smol_tools['web_search'] = DuckDuckGoSearchTool()
            self._tool_registry['web_search:web_search'] = ToolType.SMOLAGENTS_TOOL
            self._server_registry['web_search'] = ToolType.SMOLAGENTS_TOOL

            logger.debug("Initializing visit_webpage tool...")
            self._smol_tools['visit_webpage'] = VisitWebpageTool()
            self._tool_registry['visit_webpage:visit_webpage'] = ToolType.SMOLAGENTS_TOOL
            self._server_registry['visit_webpage'] = ToolType.SMOLAGENTS_TOOL

            # logger.debug("Initializing notes_agent...")
            # notes_agent = NotesAgent(self)
            # self._smol_agents['notes_agent'] = notes_agent
            # self._tool_registry['notes_agent:notes_agent'] = ToolType.SMOLAGENTS_AGENT
            # self._server_registry['notes_agent'] = ToolType.SMOLAGENTS_AGENT
            
            logger.info("ToolManager initialization completed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize built-in tools and agents: {e}", exc_info=True)
            raise

    async def call_tool(self, provider: Provider, model_id: str, tool_name: str, arguments: dict):
        """Synchronous-feeling tool call using pre-initialized session"""
        try:
            server_name, actual_tool_name = tool_name.split(":", 1)
        except ValueError:
            logger.error(f"Invalid tool name format: '{tool_name}'. Expected 'server:tool'")
            raise ValueError(f"Invalid tool name format: '{tool_name}'. Expected 'server:tool'")
        
        tool_type = self._tool_registry.get(tool_name)
        
        if tool_type is None:
            logger.error(f"Tool '{tool_name}' not found in registry")
            raise ValueError(f"Tool '{tool_name}' not found")

        try:
            if tool_type == ToolType.SMOLAGENTS_TOOL:
                tool = self._smol_tools.get(actual_tool_name)
                if tool is None:
                    logger.error(f"SMOLAGENTS tool '{tool_name}' not found in tools dictionary")
                    raise ValueError(f"SMOLAGENTS tool '{tool_name}' not found")
                logger.debug(f"Calling SMOLAGENTS tool '{tool_name}' with arguments: {arguments}")
                result = tool.run(**arguments)
                logger.debug(f"SMOLAGENTS tool '{tool_name}' completed successfully")
                return result
            
            if tool_type == ToolType.SMOLAGENTS_AGENT:
                agent = self._smol_agents.get(actual_tool_name)
                if agent is None:
                    logger.error(f"SMOLAGENTS agent '{tool_name}' not found in agents dictionary")
                    raise ValueError(f"SMOLAGENTS agent '{tool_name}' not found")
                logger.debug(f"Calling SMOLAGENTS agent '{tool_name}' with arguments: {arguments}")
                result = agent.run(provider, model_id, **arguments)
                logger.debug(f"SMOLAGENTS agent '{tool_name}' completed successfully")
                return result
            
            if tool_type == ToolType.MCP:
                session = self._sessions.get(server_name)
                if session is None:
                    logger.error(f"MCP session for server '{server_name}' not found")
                    raise ValueError(f"MCP session for server '{server_name}' not found")
                
                logger.debug(f"Calling MCP tool '{actual_tool_name}' on server '{server_name}' with arguments: {arguments}")
                try:
                    result = await asyncio.wait_for(
                        session.call_tool(actual_tool_name, arguments),
                        timeout=self._mcp_timeout
                    )
                    logger.debug(f"MCP tool '{actual_tool_name}' on server '{server_name}' completed successfully")
                    return result
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while calling MCP tool '{actual_tool_name}' on server '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"MCP tool '{actual_tool_name}' on server '{server_name}' timed out after {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Error calling MCP tool '{actual_tool_name}' on server '{server_name}': {e}", exc_info=True)
                    raise
            
            logger.error(f"Unknown tool type for '{tool_name}': {tool_type}")
            raise ValueError(f"Unknown tool type for '{tool_name}': {tool_type}")
            
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            raise
    
    async def list_tools(self, server_name: str) -> list:
        """List available tools from a specific MCP server"""
        server_type = self._server_registry.get(server_name)

        if server_type is None:
            logger.error(f"Server '{server_name}' not found in registry")
            raise ValueError(f"Unknown server '{server_name}'")

        try:
            if server_type == ToolType.SMOLAGENTS_TOOL:
                tool = self._smol_tools.get(server_name)
                if tool is None:
                    logger.error(f"SMOLAGENTS tool '{server_name}' not found in tools dictionary")
                    raise ValueError(f"SMOLAGENTS tool '{server_name}' not found")
                logger.debug(f"Listing SMOLAGENTS tool: {server_name}")
                return [tool]
            
            if server_type == ToolType.SMOLAGENTS_AGENT:
                # TODO: implement listing tools for smolagents agents
                logger.debug(f"Listing tools for SMOLAGENTS agent '{server_name}' (not yet implemented)")
                return []

            if server_type == ToolType.MCP:
                session = self._sessions.get(server_name)
                if session is None:
                    logger.error(f"MCP session for server '{server_name}' not found")
                    raise ValueError(f"MCP session for server '{server_name}' not found")
                
                logger.debug(f"Listing tools for MCP server '{server_name}'")
                try:
                    tools = await asyncio.wait_for(
                        session.list_tools(),
                        timeout=self._mcp_timeout
                    )
                    logger.debug(f"Found {len(tools)} tools for MCP server '{server_name}'")
                    return tools
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while listing tools for MCP server '{server_name}' (timeout: {self._mcp_timeout}s)")
                    raise TimeoutError(f"Failed to list tools for MCP server '{server_name}' within {self._mcp_timeout} seconds")
                except Exception as e:
                    logger.error(f"Error listing tools for MCP server '{server_name}': {e}", exc_info=True)
                    raise
            
            logger.error(f"Unknown server type for '{server_name}': {server_type}")
            raise ValueError(f"Unknown server type for '{server_name}': {server_type}")
            
        except Exception as e:
            logger.error(f"Error listing tools for server '{server_name}': {e}", exc_info=True)
            raise
    
    async def list_tool_servers(self) -> list[str]:
        """List all registered tool servers"""
        logger.debug(f"Listing {len(self._server_registry)} registered tool servers")
        return list(self._server_registry.keys())
    
    async def stop(self):
        """Cleanup on shutdown"""
        logger.info("Starting ToolManager cleanup...")

        # Clean up agents first
        for agent_name, agent in self._smol_agents.items():
            try:
                logger.debug(f"Cleaning up agent '{agent_name}'...")
                agent.cleanup()
                logger.debug(f"Agent '{agent_name}' cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up agent '{agent_name}': {e}", exc_info=True)

        # Use AsyncExitStack to properly clean up all context managers
        # This will exit all contexts in reverse order (LIFO)
        try:
            logger.debug("Closing AsyncExitStack (cleaning up all MCP sessions)...")
            await asyncio.wait_for(
                self._exit_stack.aclose(),
                timeout=self._mcp_timeout
            )
            logger.info("AsyncExitStack closed successfully")
        except asyncio.TimeoutError:
            logger.error(f"Timeout while closing AsyncExitStack (timeout: {self._mcp_timeout}s)")
        except Exception as e:
            logger.error(f"Error during AsyncExitStack cleanup: {e}", exc_info=True)

        # Clear all references
        self._sessions.clear()
        self._smol_tools.clear()
        self._smol_agents.clear()
        self._server_registry.clear()
        self._tool_registry.clear()
        self._server_params.clear()

        logger.info("ToolManager cleanup completed")