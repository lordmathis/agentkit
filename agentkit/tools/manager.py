from enum import Enum
from typing import Dict, List, Optional

from huggingface_hub import MCPClient
from mcp import ClientSession, StdioServerParameters, stdio_client
from smolagents import DuckDuckGoSearchTool, VisitWebpageTool

from agentkit.config import MCPConfig, MCPType, ProviderConfig

class ToolType(Enum):
    MCP = "mcp"
    SMOLAGENTS_TOOL = "smolagents_tool"
    SMOLAGENTS_AGENT = "smolagents_agent"

class ToolManager:
    def __init__(self, servers: Dict[str, MCPConfig]):
        self._mcp_servers = servers
        self._sessions = {}  # server_name -> ClientSession
        self._contexts = {}  # server_name -> async context manager
        self._smol_tools = {}
        self._smol_agents = {}
        self._mcp_client: MCPClient
        self._server_params: Dict[str, StdioServerParameters] = {}

        self._server_registry: Dict[str, ToolType] = {}  # server_name -> type of server
        self._tool_registry: Dict[str, ToolType] = {}  # (server_name:tool_name) -> type of tool
        
    async def start(self):
        """Initialize all MCP servers once"""
        from agentkit.tools.notes_agent import NotesAgent

        for server_name, config in self._mcp_servers.items():
            if config.type == MCPType.STDIO:
                ctx = stdio_client(StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env,
                ))
            else:
                raise ValueError(f"Unsupported MCP type: {config.type}")
            
            reader, writer = await ctx.__aenter__()
            session = ClientSession(reader, writer)
            await session.initialize()
            
            self._contexts[server_name] = ctx
            self._sessions[server_name] = session
            self._server_registry[server_name] = ToolType.MCP
            
            for tool, _ in await session.list_tools():
                self._tool_registry[f"{server_name}:{tool}"] = ToolType.MCP

            if config.type == MCPType.STDIO:
                self._server_params[server_name] = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env,
                )

        self._smol_tools['web_search'] = DuckDuckGoSearchTool()
        self._tool_registry['web_search:web_search'] = ToolType.SMOLAGENTS_TOOL
        self._server_registry['web_search'] = ToolType.SMOLAGENTS_TOOL

        self._smol_tools['visit_webpage'] = VisitWebpageTool()
        self._tool_registry['visit_webpage:visit_webpage'] = ToolType.SMOLAGENTS_TOOL
        self._server_registry['visit_webpage'] = ToolType.SMOLAGENTS_TOOL

        notes_agent = NotesAgent(self)
        self._smol_agents['notes_agent'] = notes_agent
        self._tool_registry['notes_agent:notes_agent'] = ToolType.SMOLAGENTS_AGENT
        self._server_registry['notes_agent'] = ToolType.SMOLAGENTS_AGENT

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
        for ctx in self._contexts.values():
            await ctx.__aexit__(None, None, None)
        for agent in self._smol_agents.values():
            agent.cleanup()