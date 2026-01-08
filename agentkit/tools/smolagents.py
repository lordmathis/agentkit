from typing import List, Optional
from abc import ABC, abstractmethod
from openai import OpenAI
from pydantic import BaseModel
from smolagents import OpenAIModel, ToolCallingAgent, MCPClient, Tool

from agentkit.providers.provider import Provider
from agentkit.tools.manager import ToolManager
from agentkit.tools.handler_base import ToolType


class SmolAgentConfig(BaseModel):
    """Configuration for a SmolAgent plugin."""
    
    name: str
    description: str
    parameters: dict
    tool_servers: List[str] = []
    system_prompt: str = ""

class SmolAgentsAgent:
    def __init__(
        self,
        tool_manager: ToolManager,
        name: str,
        description: str,
        parameters: dict,
        tool_servers: List[str] = [],
        system_prompt: str = "",
    ):
        self.tool_manager = tool_manager
        self.name = name
        self.description = description
        self.parameters = parameters
        self.tool_servers = tool_servers
        self.system_prompt = system_prompt
        
        # Will be initialized by tool_manager.start()
        self.mcp_client: Optional[MCPClient] = None
        self.tools: List[Tool] = []

    def initialize(self):
        """Called by ToolManager.start() to set up MCP client and tools"""
        # Get MCP server params for this agent

        mcp_params = []

        for server_name in self.tool_servers:
            server_type = self.tool_manager.get_server_type(server_name)

            if server_type == ToolType.MCP:
                # For MCP servers, we need to access the handler's sessions
                # This is a bit of a hack, but maintains backward compatibility
                if hasattr(self.tool_manager._mcp_handler, '_sessions'):
                    session = self.tool_manager._mcp_handler._sessions.get(server_name)
                    if session:
                        # We need to convert this to MCP params for the MCPClient
                        # This might need adjustment based on how MCPClient works
                        pass

            if server_type == ToolType.SMOLAGENTS_TOOL:
                # Add smolagents tool directly
                if hasattr(self.tool_manager._smol_handler, '_tools'):
                    tool = self.tool_manager._smol_handler._tools.get(server_name)
                    if tool:
                        self.tools.append(tool)

            if server_type == ToolType.SMOLAGENTS_AGENT:
                raise ValueError("Nested SmolAgentsAgent is not supported")
        
        # Initialize MCP client if needed
        if mcp_params:
            self.mcp_client = MCPClient(mcp_params)
            self.mcp_client.__enter__()
            self.tools.extend(self.mcp_client.get_tools())
        

    def run(self, provider: Provider, model_id: str, prompt: str) -> str:
        """Run the agent with its configured tools"""
        if not self.tools and not self.mcp_client:
            # No tools configured, just use the model
            pass
        
        client_kwargs = provider.get_client_kwargs()
        model = OpenAIModel(
            model_id=model_id,
            client_kwargs=client_kwargs,
        )

        agent = ToolCallingAgent(
            model=model,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

        return str(agent.run(prompt))
    
    def cleanup(self):
        """Called by ToolManager.stop() to clean up MCP client"""
        if self.mcp_client:
            self.mcp_client.__exit__(None, None, None)


class SmolAgentPlugin(SmolAgentsAgent, ABC):
    """Base plugin class for agent discovery."""
    
    def __init__(self, tool_manager: ToolManager):
        config = self.configure()
        super().__init__(
            tool_manager=tool_manager,
            name=config.name,
            description=config.description,
            parameters=config.parameters,
            tool_servers=config.tool_servers,
            system_prompt=config.system_prompt,
        )
    
    @abstractmethod
    def configure(self) -> SmolAgentConfig:
        """Return agent configuration."""
        pass