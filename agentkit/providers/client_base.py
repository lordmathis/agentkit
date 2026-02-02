"""Base class and implementations for different LLM API clients."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence
import httpx
import json


class LLMClient(ABC):
    """Abstract base class for LLM API clients."""
    
    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from the provider.
        
        Returns:
            List of model dictionaries
        """
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: Sequence[Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a chat completion.
        
        Args:
            model: Model identifier
            messages: List of message dictionaries
            tools: Optional list of tool definitions
            temperature: Optional temperature parameter
            max_tokens: Optional max tokens parameter
            
        Returns:
            Response dictionary in OpenAI format
        """
        pass


class OpenAIClient(LLMClient):
    """Client for OpenAI-compatible APIs."""
    
    def __init__(self, client: Any):
        """Initialize with an OpenAI client instance.
        
        Args:
            client: openai.OpenAI instance
        """
        self.client = client
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenAI API."""
        models = self.client.models.list()
        return [model.model_dump() if hasattr(model, 'model_dump') else model.dict() 
                for model in models.data]
    
    async def chat_completion(
        self,
        model: str,
        messages: Sequence[Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a chat completion using OpenAI API."""
        api_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        
        if temperature is not None:
            api_params["temperature"] = temperature
        
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens
        
        if tools:
            api_params["tools"] = tools
        
        response = self.client.chat.completions.create(**api_params)
        return response.model_dump()


class AnthropicClient(LLMClient):
    """Client for Anthropic API."""
    
    def __init__(self, client: Any):
        """Initialize with an Anthropic client instance.
        
        Args:
            client: anthropic.Anthropic instance
        """
        self.client = client
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from Anthropic API."""
        models = self.client.models.list()
        # Convert Anthropic model objects to dicts
        return [model.model_dump() if hasattr(model, 'model_dump') else model.dict() 
                for model in models.data]
    
    async def chat_completion(
        self,
        model: str,
        messages: Sequence[Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a chat completion using Anthropic API.
        
        Converts OpenAI-style messages to Anthropic format and response back to OpenAI format.
        """
        # Extract system messages
        system_messages = [m for m in messages if m.get("role") == "system" or m.get("role") == "developer"]
        system_prompt = "\n\n".join(m.get("content", "") for m in system_messages) if system_messages else None
        
        # Convert messages to Anthropic format (exclude system messages)
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role")
            if role in ["system", "developer"]:
                continue
            
            # Map OpenAI roles to Anthropic roles
            if role == "assistant":
                anthropic_role = "assistant"
            elif role == "user":
                anthropic_role = "user"
            elif role == "tool":
                # Tool results in Anthropic are handled differently
                anthropic_role = "user"
            else:
                continue
            
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            
            anthropic_msg: Dict[str, Any] = {"role": anthropic_role}
            
            # Handle tool calls
            if tool_calls:
                anthropic_msg["content"] = []
                if content:
                    anthropic_msg["content"].append({"type": "text", "text": content})
                
                for tc in tool_calls:
                    # Parse arguments if they're a JSON string
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    
                    anthropic_msg["content"].append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": args
                    })
            elif role == "tool":
                # Tool result
                anthropic_msg["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id"),
                    "content": content
                }]
            else:
                anthropic_msg["content"] = content
            
            anthropic_messages.append(anthropic_msg)
        
        # Convert tools to Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    anthropic_tools.append({
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "input_schema": func.get("parameters", {})
                    })
        
        # Prepare API call
        api_params: Dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,  # Anthropic requires max_tokens
        }
        
        if system_prompt:
            api_params["system"] = system_prompt
        
        if temperature is not None:
            api_params["temperature"] = temperature
        
        if anthropic_tools:
            api_params["tools"] = anthropic_tools
        
        # Call Anthropic API
        response = self.client.messages.create(**api_params)
        
        # Convert response to OpenAI format
        return self._convert_response_to_openai(response)
    
    def _convert_response_to_openai(self, response: Any) -> Dict[str, Any]:
        """Convert Anthropic response to OpenAI format."""
        # Extract content and tool calls from Anthropic response
        content_parts = []
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input) if isinstance(block.input, dict) else block.input
                    }
                })
        
        content = "\n".join(content_parts) if content_parts else None
        
        # Build OpenAI-style response
        message: Dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        return {
            "id": response.id,
            "object": "chat.completion",
            "created": int(response.model_dump().get("created_at", 0)) if hasattr(response, "created_at") else 0,
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": response.stop_reason,
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
        }
