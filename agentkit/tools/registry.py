from typing import Dict, Optional


from agentkit.config import MCPConfig
from agentkit.tools.mcp import MCPServerTool
from agentkit.tools.notes_agent import NotesAgent
from agentkit.tools.tool import AgentKitTool

class ToolRegistry:
    def __init__(self, config: Dict[str, MCPConfig]):
        self._tools: Dict[str, AgentKitTool] = {}
        self._register_tools()
        self._register_mcps(config)
    
    def _register_tools(self):
        notes_agent = NotesAgent(self)
        self._tools["notes_agent"] = notes_agent

    def _register_mcps(self, config: Dict[str, MCPConfig]):
        for mcp_name, mcp_config in config.items():
            mcp_tool = MCPServerTool(
                command=mcp_config.command,
                args=mcp_config.args,
                env=mcp_config.env
            )
            self._tools[mcp_name] = mcp_tool
    
    def get_tools(self) -> Dict[str, AgentKitTool]:    
        return self._tools

    def get_tool(self, name: str) -> Optional[AgentKitTool]:
        return self._tools.get(name)
