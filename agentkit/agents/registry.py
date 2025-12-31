from typing import Dict, Optional, List, Any
import os
import importlib.util
import inspect
from agentkit.agents import Agent


class AgentRegistry:
    _agents: Dict[str, Agent] = {}

    @classmethod
    def register_all(
        cls,
    ) -> None:
        # Discover and register all agents in this folder
        agents_folder = os.path.dirname(__file__)
        skip_files = ["registry.py", "agent.py", "__init__.py"]
        agent_files = [
            f
            for f in os.listdir(agents_folder)
            if f.endswith(".py") and f not in skip_files
        ]
        for filename in agent_files:
            # Construct module path
            module_path = os.path.join(agents_folder, filename)
            module_name = f"agentkit.agents.{filename[:-3]}"

            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find all classes that implement the Agent protocol
            agent_class = None
            for _, obj in inspect.getmembers(module, inspect.isclass):
                # Skip imported classes (only get classes defined in this module)
                if obj.__module__ != module_name:
                    continue
                # Check if it implements the Agent protocol
                if isinstance(obj, type) and issubclass(obj, Agent):
                    agent_class = obj
                    break

            # Instantiate and register the agent
            if agent_class is not None:
                try:
                    agent_instance = agent_class()
                    # Use the class name (without "Agent" suffix if present) as the registration name
                    agent_name = agent_class.__name__
                    if agent_name.endswith("Agent"):
                        agent_name = agent_name[:-5]
                    # Convert from CamelCase to kebab-case
                    agent_name = ''.join(['-' + c.lower() if c.isupper() else c for c in agent_name]).lstrip('-')
                    cls.register_agent(agent_name, agent_instance)
                except Exception as e:
                    print(f"Warning: Failed to instantiate agent from {filename}: {e}")
            

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
        for agent_name, agent in cls._agents.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": agent_name,
                        "description": agent.get_description(),
                        "parameters": agent.get_parameters(),
                    },
                }
            )
        return tools
