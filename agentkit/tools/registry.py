from enum import Enum
from typing import Dict, Optional, Tuple, TypeAlias


from agentkit.config import MCPConfig
from agentkit.tools.mcp import MCPServerTool
from agentkit.tools.notes_agent import NotesAgent
from agentkit.tools.smolagents import SmolAgentsTool

class ToolType(Enum):
    MCP = "mcp"
    SMOLAGENTS = "smolagents"

BaseTool: TypeAlias = MCPServerTool | SmolAgentsTool

class ToolRegistry:
    def __init__(self, config: Dict[str, MCPConfig]):
        self._tools: Dict[str, ToolType] = {}
        self._mcps: Dict[str, MCPServerTool] = {}
        self._smolagents_tools: Dict[str, SmolAgentsTool] = {}

        self._register_tools()
        self._register_mcps(config)
    
    def _register_tools(self):
        self._smolagents_tools["notes_agent"] = NotesAgent(self)

    def _register_mcps(self, config: Dict[str, MCPConfig]):
        for mcp_name, mcp_config in config.items():
            mcp_tool = MCPServerTool(
                command=mcp_config.command,
                args=mcp_config.args,
                env=mcp_config.env
            )
            self._mcps[mcp_name] = mcp_tool

    def get_tools(self) -> Dict[str, Tuple[ToolType, BaseTool]]:
        all_tools = {}
        for name, tool in self._mcps.items():
            all_tools[name] = (ToolType.MCP, tool)
        for name, tool in self._smolagents_tools.items():
            all_tools[name] = (ToolType.SMOLAGENTS, tool)
        return all_tools
    
    def get_tool(self, name: str) -> Optional[Tuple[ToolType, BaseTool]]:
        if name in self._mcps:
            return (ToolType.MCP, self._mcps[name])
        if name in self._smolagents_tools:
            return (ToolType.SMOLAGENTS, self._smolagents_tools[name])
        return None
    
    def get_mcps(self) -> Dict[str, MCPServerTool]:
        return self._mcps
    
    def get_mcp(self, name: str) -> Optional[MCPServerTool]:
        return self._mcps.get(name)

    def get_smolagents_tools(self) -> Dict[str, SmolAgentsTool]:
        return self._smolagents_tools
    
    def get_smolagents_tool(self, name: str) -> Optional[SmolAgentsTool]:
        return self._smolagents_tools.get(name)
