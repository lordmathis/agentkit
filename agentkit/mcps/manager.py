from mcp import StdioServerParameters
from smolagents import MCPClient

from agentkit.config import MCPConfig


class MCPManager:

    _clients: dict[str, MCPClient] = {}
    _mcp_config: dict[str, MCPConfig] = {}

    @classmethod
    def configure(cls, config: dict[str, MCPConfig]):
        cls._mcp_config = config

    @classmethod
    def get_client(cls, name: str) -> MCPClient | None:
        if name in cls._clients:
            return cls._clients[name]
        
        if name not in cls._mcp_config:
            return None
        
        cfg = cls._mcp_config[name]

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
        cls._clients[name] = MCPClient([server], structured_output=False)
        return cls._clients[name]
    
    @classmethod
    def close_all(cls):
        for client in cls._clients.values():
            client.disconnect()
        cls._clients.clear()