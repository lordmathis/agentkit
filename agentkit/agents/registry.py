from typing import Dict, Optional, List, Any
from agentkit.agents.agent import Agent

class AgentRegistry():
    _agents: Dict[str, Agent] = {}

    @classmethod
    def register_agent(cls, name: str, agent: Agent) -> None:
        """Register a new agent."""
        if name in cls._agents:
            return
        cls._agents[name] = agent

    @classmethod
    def get_agent(cls, name: str) -> Optional[Agent]:
        """Retrieve an agent by name."""
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        """List all registered agents as OpenAI tool definitions."""
        tools = []
        for agent_name in cls._agents.keys():
            tools.append({
                "type": "function",
                "function": {
                    "name": agent_name,
                    "description": f"Run the {agent_name} agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to send to the agent"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            })
        return tools