from typing import Dict, List, Protocol, runtime_checkable

@runtime_checkable
class Agent(Protocol):
    def chat(self, messages: List[Dict[str, str]]) -> str:
        ...