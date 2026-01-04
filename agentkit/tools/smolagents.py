from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, List

from smolagents import OpenAIModel, ToolCallingAgent, MCPClient

from agentkit.tools.mcp import MCPServerTool
from agentkit.tools.registry import ToolRegistry
from agentkit.tools.tool import AgentKitTool

class SmolAgentsSession:
    def __init__(self, agent):
        self.agent = agent
    
    async def __aenter__(self):
        # Setup logic here if needed
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup logic here if needed
        pass

@dataclass
class ModelConfig:
    api_base: str
    api_key: str
    model_id: str
    model_kwargs: dict

class SmolAgentsTool(AgentKitTool):
    name: str
    description: str
    parameters: dict

    def __init__(self, tool_registry: ToolRegistry, name: str, description: str, parameters: dict, system_prompt: str = "", tool_names: List[str] = []):
        self.tool_registry = tool_registry
        self.tool_names = tool_names
        self.name = name
        self.description = description
        self.parameters = parameters
        self.system_prompt = system_prompt

    @asynccontextmanager
    async def connect(self, model_config: ModelConfig) -> AsyncGenerator[SmolAgentsSession, None]:
        """Connect to the underlying MCP session if applicable."""
        model = OpenAIModel(
            model_id=model_config.model_id,
            api_base=model_config.api_base,
            api_key=model_config.api_key,
            **model_config.model_kwargs
        )

        all_tools = []
        for tool_name in self.tool_names:
            tool = self.tool_registry.get_tool(tool_name)
            if tool is None:
                print(f"Tool {tool_name} not found in tool registry")
                continue
            if not isinstance(tool, MCPServerTool):
                print(f"Non-MCP tool {tool_name} cannot be used with Smolagents")
                continue
            all_tools.append(tool.server_params)

        with MCPClient(all_tools) as tools:

            self.agent = ToolCallingAgent(
                    tools=tools,
                    model=model,
                    add_base_tools=True,
                )

            session = SmolAgentsSession(self.agent)
            async with session as s:
                yield s
                
    async def call_tool(self, session: SmolAgentsSession, _, prompt: str) -> dict:
        """Call a tool by name with given arguments."""
        if self.system_prompt:
            prompt = f"INSTRUCTIONS: {self.system_prompt}\n\nUSER QUERY: {prompt}"
        return session.agent.run(prompt)
