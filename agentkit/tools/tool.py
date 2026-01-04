from abc import ABC, abstractmethod

class AgentKitTool(ABC):
    
    @abstractmethod
    async def connect(self, **kwargs):
        pass

    @abstractmethod
    async def call_tool(self, session, tool_name: str, **kwargs) -> dict:
        pass