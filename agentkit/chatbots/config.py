from typing import List, Optional

from pydantic import BaseModel


class ModelParams(BaseModel):
    """Model parameters for chatbot configuration."""

    max_iterations: Optional[int] = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatConfig(BaseModel):
    """Configuration for a chat session."""

    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[ModelParams] = None
