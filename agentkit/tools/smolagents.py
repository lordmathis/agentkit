from dataclasses import dataclass
from typing import Any, List

from mcp import StdioServerParameters
from smolagents import OpenAIModel, ToolCallingAgent, MCPClient

from agentkit.tools.mcp import MCPServerTool
from agentkit.tools.registry import ToolRegistry

@dataclass
class ModelConfig:
    api_base: str
    api_key: str
    model_id: str
    model_kwargs: dict

class SmolAgentsInstance:

    model: OpenAIModel
    agent: ToolCallingAgent
    tools: list[StdioServerParameters | dict[str, Any]]
    system_prompt: str = ""

    def __init__(self, model_config: ModelConfig, tool_registry: ToolRegistry, mcp_ids: List[str] = [], system_prompt: str = ""):

        self.model = OpenAIModel(
            model_id=model_config.model_id,
            api_base=model_config.api_base,
            api_key=model_config.api_key,
            **model_config.model_kwargs
        )
        self.system_prompt = system_prompt

        self.tools = []
        for mcp_id in mcp_ids:
            tool = tool_registry.get_mcp(mcp_id)
            if tool is None:
                print(f"Tool {mcp_id} not found in tool registry")
                continue
            if not isinstance(tool, MCPServerTool):
                print(f"Non-MCP tool {mcp_id} cannot be used with Smolagents")
                continue
            self.tools.append(tool.server_params)

       
    def run(self, prompt: str) -> dict:

        with MCPClient(self.tools) as mcp_tools:
            if self.system_prompt:
                prompt = f"INSTRUCTIONS: {self.system_prompt}\n\nUSER QUERY: {prompt}"

            agent = ToolCallingAgent(
                model=self.model,
                tools=mcp_tools
            )
            response = agent.run(prompt)
            return response.dict()


class SmolAgentsTool():
    name: str
    description: str
    parameters: dict

    def __init__(self, tool_registry: ToolRegistry, name: str, description: str, parameters: dict, system_prompt: str = "", mcp_ids: List[str] = []):
        self.tool_registry = tool_registry
        self.mcp_ids = mcp_ids
        self.name = name
        self.description = description
        self.parameters = parameters
        self.system_prompt = system_prompt

    def create_instance(self, model_config: ModelConfig) -> SmolAgentsInstance:
        """Factory method - creates a new agent instance"""
        return SmolAgentsInstance(
            model_config=model_config,
            tool_registry=self.tool_registry,
            mcp_ids=self.mcp_ids,
            system_prompt=self.system_prompt
        )

