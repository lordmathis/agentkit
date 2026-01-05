from contextlib import asynccontextmanager
from typing import List

from mcp import ClientSession, StdioServerParameters, stdio_client


class MCPServerTool():

    server_params: StdioServerParameters

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
       self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

    @asynccontextmanager
    async def connect(self, **kwargs):
        """Context manager for MCP session lifecycle"""
        async with stdio_client(self.server_params) as (read, write):
            session = ClientSession(read, write)
            await session.initialize()
            
            try:
                yield session
            finally:
                pass

    async def list_tools(self, session: ClientSession) -> List[dict]:
        """Retrieve the list of tools from the MCP session."""
        tools_list = await session.list_tools()

        # Convert to OpenAI format
        openai_tools = []
        for tool in tools_list.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })

        return openai_tools