from typing import Protocol, runtime_checkable, Dict, Any

@runtime_checkable
class Agent(Protocol):
    def run(self, prompt: str) -> str:
        ...

    def get_description(self) -> str:
        """Return the description of what this agent does."""
        ...

    def get_parameters(self) -> Dict[str, Any]:
        """Return the JSON schema for the agent's parameters."""
        ...