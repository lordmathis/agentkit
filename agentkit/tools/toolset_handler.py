from typing import Callable, Any, Dict, Optional, List, TYPE_CHECKING
from abc import ABC
from pydantic import BaseModel
import inspect
import logging

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
    
    async def initialize(self) -> None:
        """Discover and register decorated tool functions"""
        # Find all methods decorated with @tool
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '_tool_definition'):
                tool_def = method._tool_definition
                # Create a new ToolDefinition with the bound method instead of the unbound function
                bound_tool_def = ToolDefinition(
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=tool_def.parameters,
                    func=method  # Use the bound method, not the original function
                )
                self._tools[tool_def.name] = bound_tool_def
                logger.info(f"Registered tool '{tool_def.name}' in toolset '{self.server_name}'")
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool function"""
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found in toolset '{self.server_name}'")
        
        logger.debug(f"Calling tool '{tool_name}' with arguments: {arguments}")
        
        # Call the function (handle both sync and async)
        if inspect.iscoroutinefunction(tool_def.func):
            result = await tool_def.func(**arguments)
        else:
            result = tool_def.func(**arguments)
        
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
        return await self._tool_manager.call_tool(call_name, arguments)


def tool(description: str, parameters: Optional[Dict[str, Any]] = None):
    """Decorator to mark a method as a tool
    
    Args:
        description: Description of what the tool does
        parameters: JSON Schema for parameters (auto-generated from type hints if not provided)
    """
    def decorator(func: Callable) -> Callable:
        # Auto-generate JSON Schema from type hints if not provided
        if parameters is None:
            schema = _generate_schema_from_signature(func)
        else:
            schema = parameters
        
        # Store tool metadata on the function
        func._tool_definition = ToolDefinition(
            name=func.__name__,
            description=description,
            parameters=schema,
            func=func
        )
        
        return func
    
    return decorator


def _generate_schema_from_signature(func: Callable) -> Dict[str, Any]:
    """Generate JSON Schema from function signature

    Note: This function provides basic type mapping. For complex types (list, dict, Union, etc.),
    it's recommended to explicitly provide the JSON Schema in the @tool decorator.
    """
    sig = inspect.signature(func)
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue

        # Basic type mapping
        param_type = param.annotation
        if param_type == str:
            properties[param_name] = {"type": "string"}
        elif param_type == int:
            properties[param_name] = {"type": "integer"}
        elif param_type == float:
            properties[param_name] = {"type": "number"}
        elif param_type == bool:
            properties[param_name] = {"type": "boolean"}
        elif hasattr(param_type, "__origin__"):
            # Handle generic types like list, dict
            if param_type.__origin__ == list:
                properties[param_name] = {"type": "array"}
            elif param_type.__origin__ == dict:
                properties[param_name] = {"type": "object"}
            else:
                properties[param_name] = {"type": "string"}  # Default fallback
        else:
            properties[param_name] = {"type": "string"}  # Default fallback

        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }