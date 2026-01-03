from typing import Dict, List, Tuple

from agentkit.config import MCPConfig
from agentkit.tools.mcp_manager import MCPManager
from agentkit.tools.notes_agent import NotesAgent
from agentkit.tools.tool import Tool, ToolSource

class ToolRegistry:
    def __init__(self, config: Dict[str, MCPConfig]):
        self._tool_sources = Dict[str, ToolSource] = {}
        self._tools: Dict[str, Tool] = {}
    
        # Later: load OpenAPI tools, custom functions, etc.

    def _register_tools(self):
        notes_agent = NotesAgent(self)
        self._tools["Notes Agent"] = notes_agent

    def _register_mcps(self):
        # Register MCP tools from MCPManager
        for mcp_name in self.mcp_manager._mcp_config.keys():
            mcp_client = self.mcp_manager.get_client(mcp_name)
            if mcp_client:
                tool = Tool.from_mcp_client(mcp_name, mcp_client)
                self._tools[mcp_name] = tool
    
    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)
    
    def list_tool_sources(self) -> List[Tuple[str, str]]:
        pass

    def get_llm_tools(self) -> List[Tool]:
        pass