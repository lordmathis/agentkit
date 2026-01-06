from enum import Enum
from typing import Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from smolagents import DuckDuckGoSearchTool, VisitWebpageTool, MCPClient

from agentkit.config import MCPConfig, MCPType, ProviderConfig

class ToolType(Enum):
    MCP = "mcp"
    SMOLAGENTS_TOOL = "smolagents_tool"
    SMOLAGENTS_AGENT = "smolagents_agent"

class ToolManager:
    def __init__(self, servers: Dict[str, MCPConfig]):
        self._mcp_servers = servers
        self._sessions = {}  # server_name -> ClientSession
        self._exit_stack = AsyncExitStack()  # Manages all context managers
        self._smol_tools = {}
        self._smol_agents = {}
        self._mcp_client: MCPClient
        self._server_params: Dict[str, StdioServerParameters] = {}

        self._server_registry: Dict[str, ToolType] = {}  # server_name -> type of server
        self._tool_registry: Dict[str, ToolType] = {}  # (server_name:tool_name) -> type of tool
        
    async def start(self):
        """Initialize all MCP servers once"""
        print(f"DEBUG: ToolManager.start() - Starting with {len(self._mcp_servers)} MCP servers")
        from agentkit.tools.notes_agent import NotesAgent

        for server_name, config in self._mcp_servers.items():
            print(f"DEBUG: Initializing MCP server '{server_name}' (type: {config.type})")
            print(f"DEBUG:   Command: {config.command}, Args: {config.args}")

            if config.type == MCPType.STDIO:
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env,
                )
            else:
                raise ValueError(f"Unsupported MCP type: {config.type}")

            print(f"DEBUG: Creating stdio client for '{server_name}'...")
            # Use AsyncExitStack to properly manage context managers
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            print(f"DEBUG: Connected to stdio client for '{server_name}', creating session...")
            session = ClientSession(read_stream, write_stream)

            # Enter session context via exit stack
            await self._exit_stack.enter_async_context(session)

            print(f"DEBUG: Initializing session for '{server_name}'...")
            await session.initialize()
            print(f"DEBUG: Session initialized for '{server_name}'")

            self._sessions[server_name] = session
            self._server_registry[server_name] = ToolType.MCP

            print(f"DEBUG: Listing tools for '{server_name}'...")
            for tool, _ in await session.list_tools():
                print(f"DEBUG:   Found tool: {tool}")
                self._tool_registry[f"{server_name}:{tool}"] = ToolType.MCP

            if config.type == MCPType.STDIO:
                self._server_params[server_name] = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env,
                )
            print(f"DEBUG: Finished initializing '{server_name}'")

        print("DEBUG: Initializing web_search tool...")
        self._smol_tools['web_search'] = DuckDuckGoSearchTool()
        self._tool_registry['web_search:web_search'] = ToolType.SMOLAGENTS_TOOL
        self._server_registry['web_search'] = ToolType.SMOLAGENTS_TOOL

        print("DEBUG: Initializing visit_webpage tool...")
        self._smol_tools['visit_webpage'] = VisitWebpageTool()
        self._tool_registry['visit_webpage:visit_webpage'] = ToolType.SMOLAGENTS_TOOL
        self._server_registry['visit_webpage'] = ToolType.SMOLAGENTS_TOOL

        print("DEBUG: Initializing notes_agent...")
        notes_agent = NotesAgent(self)
        self._smol_agents['notes_agent'] = notes_agent
        self._tool_registry['notes_agent:notes_agent'] = ToolType.SMOLAGENTS_AGENT
        self._server_registry['notes_agent'] = ToolType.SMOLAGENTS_AGENT
        print("DEBUG: ToolManager.start() completed")

    async def call_tool(self, provider_cfg: ProviderConfig, model_id: str, tool_name: str, arguments: dict):
        """Synchronous-feeling tool call using pre-initialized session"""
        server_name, actual_tool_name = tool_name.split(":", 1)
        tool_type = self._tool_registry.get(tool_name)

        if tool_type == ToolType.SMOLAGENTS_TOOL:
            tool = self._smol_tools.get(actual_tool_name)
            if tool is None:
                raise ValueError(f"SMOLAGENTS tool '{tool_name}' not found")
            return tool.run(**arguments)
        
        if tool_type == ToolType.SMOLAGENTS_AGENT:
            agent = self._smol_agents.get(actual_tool_name)
            if agent is None:
                raise ValueError(f"SMOLAGENTS agent '{tool_name}' not found")
            return agent.run(provider_cfg, model_id, **arguments)
        
        if tool_type != ToolType.MCP:
            session = self._sessions[server_name]
            result = await session.call_tool(actual_tool_name, arguments)
            return result
    
    async def list_tools(self, server_name: str) -> list:
        """List available tools from a specific MCP server"""
        server_type = self._server_registry.get(server_name)

        if server_type == ToolType.SMOLAGENTS_TOOL:
            tool = self._smol_tools.get(server_name)
            if tool is None:
                raise ValueError(f"SMOLAGENTS tool '{server_name}' not found")
            return [tool]
        
        if server_type == ToolType.SMOLAGENTS_AGENT:
            # TODO: implement listing tools for smolagents agents
            return []

        if server_type != ToolType.MCP:
            session = self._sessions[server_name]
            return session.list_tools()
        
        raise ValueError(f"Unknown server '{server_name}'")
    
    async def list_tool_servers(self) -> list[str]:
        """List all registered tool servers"""
        return list(self._server_registry.keys())
    
    async def stop(self):
        """Cleanup on shutdown"""
        print("DEBUG: ToolManager.stop() - Starting cleanup...")

        # Clean up agents first
        for agent in self._smol_agents.values():
            try:
                agent.cleanup()
            except Exception as e:
                print(f"DEBUG: Error cleaning up agent: {e}")

        # Use AsyncExitStack to properly clean up all context managers
        # This will exit all contexts in reverse order (LIFO)
        try:
            print("DEBUG: Closing AsyncExitStack (this will clean up all MCP sessions)...")
            await self._exit_stack.aclose()
            print("DEBUG: AsyncExitStack closed successfully")
        except Exception as e:
            print(f"DEBUG: Error during AsyncExitStack cleanup: {e}")

        # Clear all references
        self._sessions.clear()

        print("DEBUG: ToolManager.stop() - Cleanup complete")