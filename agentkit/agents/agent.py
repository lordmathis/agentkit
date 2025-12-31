from typing import Protocol, runtime_checkable

@runtime_checkable
class Agent(Protocol):
    def run(self, prompt: str) -> str:
        ...