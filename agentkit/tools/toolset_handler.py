import inspect
import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from agentkit.providers import Provider

if TYPE_CHECKING:
    from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Metadata for a tool function"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    func: Callable

    class Config:
        arbitrary_types_allowed = True


class ToolSetHandler(ABC):
    """Base class for function-based tool handlers"""

    def __init__(self, name: str, tool_manager: Optional["ToolManager"] = None):
        self.server_name = name
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_manager: Optional["ToolManager"] = tool_manager

        self._provider: Optional[Provider] = None
        self._model_id: Optional[str] = None

    def set_tool_manager(self, tool_manager: "ToolManager") -> None:
        """Set the ToolManager instance for cross-tool calls

        Args:
            tool_manager: The ToolManager instance to use for calling other tools
        """
        if self._tool_manager is None:
            self._tool_manager = tool_manager
        else:
            logger.warning(f"ToolManager already set for toolset '{self.server_name}', ignoring new value")

    def get_persistent_storage(self):
        self._tool_manager.get_persistent_storage(self.server_name)

    def set_model_context(self, provider: Provider, model_id: str) -> None:
        self._provider = provider
        self._model_id = model_id
    
    async def initialize(self) -> None:
        """Discover and register decorated tool functions"""
        # Find all methods decorated with @tool
        for _, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not hasattr(method, '_tool_definition'):
                continue

            tool_def = method._tool_definition
            # Create a new ToolDefinition with the bound method instead of the unbound function
            bound_tool_def = ToolDefinition(
                name=tool_def.name,
                description=tool_def.description,
                parameters=tool_def.parameters,
                func=method
            )
            self._tools[tool_def.name] = bound_tool_def
            logger.info(f"Registered tool '{tool_def.name}' in toolset '{self.server_name}'")
    
    async def call_tool(self, tool_name: str, arguments: dict, provider: Provider, model_id: str) -> Any:
        """Execute a tool function"""
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found in toolset '{self.server_name}'")
        self.set_model_context(provider, model_id)

        logger.debug(f"[{self.server_name}] Calling tool '{tool_name}' with arguments: {arguments}")

        if inspect.iscoroutinefunction(tool_def.func):
            result = await tool_def.func(**arguments)
        else:
            result = tool_def.func(**arguments)

        logger.debug(f"[{self.server_name}] Tool '{tool_name}' returned: type={type(result)}, value={result}")
        return result
    
    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools"""
        return list(self._tools.values())
    
    async def cleanup(self) -> None:
        """Default cleanup does nothing"""
        pass
    
    async def call_other_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Helper to call tools from other servers (including MCP)"""
        if not self._tool_manager:
            raise RuntimeError("ToolManager not set")

        call_name = f"{server_name}__{tool_name}"
        logger.debug(f"[{self.server_name}] Calling {call_name}")

        result = await self._tool_manager.call_tool(call_name, arguments, self._provider, self._model_id)
        return result


def tool(description: str, parameters: Dict[str, Any]):
    """Decorator to mark a method as a tool
    
    Args:
        description: Description of what the tool does
        parameters: JSON Schema for parameters (auto-generated from type hints if not provided)
    """
    def decorator(func: Callable) -> Callable:
        func._tool_definition = ToolDefinition(
            name=func.__name__,
            description=description,
            parameters=parameters,
            func=func
        )
        
        return func
    
    return decorator
