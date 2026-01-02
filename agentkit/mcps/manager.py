from mcp import StdioServerParameters
from smolagents import MCPClient

from agentkit.config import MCPConfig


class MCPManager:

    _clients: dict[str, MCPClient]
    _mcp_config: dict[str, MCPConfig]

    def __init__(self, config: dict[str, MCPConfig]) -> None:
        self._mcp_config = config
        self._clients = {}

    def get_client(self, name: str) -> MCPClient | None:
        if name in self._clients:
            return self._clients[name]
        
        if name not in self._mcp_config:
            return None
        
        cfg = self._mcp_config[name]

        # Patch MCP tools to add empty properties if missing
        import mcpadapt.smolagents_adapter
        original_adapt = mcpadapt.smolagents_adapter.SmolAgentsAdapter.adapt

        def patched_adapt(self, func, mcp_tool):
            if hasattr(mcp_tool, 'inputSchema') and mcp_tool.inputSchema:
                schema = mcp_tool.inputSchema
                if isinstance(schema, dict) and 'properties' not in schema:
                    schema['properties'] = {}
            return original_adapt(self, func, mcp_tool)

        mcpadapt.smolagents_adapter.SmolAgentsAdapter.adapt = patched_adapt
        # End patch

        server = StdioServerParameters(
            command=cfg.command,
            args=cfg.args,
            env=cfg.env,
        )
        self._clients[name] = MCPClient([server], structured_output=False)
        return self._clients[name]
    
    def close_all(self):
        for client in self._clients.values():
            client.disconnect()
        self._clients.clear()