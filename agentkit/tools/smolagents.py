from typing import List

from smolagents import OpenAIModel, ToolCallingAgent, MCPClient

from agentkit.tools.manager import ToolManager


class SmolAgentsAgent:
    name: str
    description: str
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The input prompt for the agent",
            },
        },
        "required": ["prompt"],
    }
    system_prompt: str = ""

    def __init__(
        self,
        tool_manager: ToolManager,
        name: str,
        description: str,
        parameters: dict,
        system_prompt: str = "",
        tool_names: List[str] = [],
    ):
        self.tool_manager = tool_manager
        self.tool_names = tool_names
        self.name = name
        self.description = description
        self.parameters = parameters
        self.system_prompt = system_prompt

    def get_description(self) -> str:
        return self.description

    def get_parameters(self) -> dict:
        return self.parameters

    def run(self, provider_cfg, model_id, prompt: str) -> dict:
        model = OpenAIModel(
            api_base=provider_cfg.api_base,
            api_key=provider_cfg.api_key,
            model_id=model_id,
        )

        mcp_client, tools = ...

        with MCPClient(...) as tools:
            agent = ToolCallingAgent(
                model=model,
                tools=tools,
            )

            full_prompt = prompt
            if self.system_prompt:
                full_prompt = (
                    f"INSTRUCTIONS: {self.system_prompt}\n\nUSER QUERY: {prompt}"
                )

            return agent.run(full_prompt).dict()
