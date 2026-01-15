from typing import List, Optional

from agentkit.chatbots.chatbot import Chatbot
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager


class ChatbotFactory:
    """Factory for creating chatbot instances dynamically."""

    @staticmethod
    def create_chatbot(
        model: str,
        provider_registry: ProviderRegistry,
        chatbot_registry: ChatbotRegistry,
        tool_manager: ToolManager,
        system_prompt: Optional[str] = None,
        tool_servers: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_iterations: Optional[int] = None,
    ) -> Chatbot:
        """
        Create chatbot from model string.

        Args:
            model: Model identifier. Can be:
                - "provider:model_id" for direct provider models (e.g., "llamactl:gpt-oss-20b")
                - "chatbot_name" for predefined chatbots (e.g., "Assistant")
            provider_registry: Registry of available providers
            chatbot_registry: Registry of predefined chatbots
            tool_manager: Tool manager instance
            system_prompt: Optional system prompt override
            tool_servers: Optional tool servers override
            temperature: Temperature for model generation
            max_tokens: Maximum tokens for model generation
            max_iterations: Maximum iterations for agent loop

        Returns:
            BaseChatbot instance configured with the specified settings

        Raises:
            ValueError: If model cannot be found or is invalid
        """
        # Check if model is a provider:model_id format
        if ":" in model:
            provider_name, model_id = model.split(":", 1)
            provider = provider_registry.get_provider(provider_name)

            if not provider:
                raise ValueError(f"Provider '{provider_name}' not found")

            # Create a new chatbot instance with provider config
            return Chatbot(
                provider=provider,
                tool_manager=tool_manager,
                system_prompt=system_prompt or "",
                model_id=model_id,
                tool_servers=tool_servers or [],
                max_iterations=max_iterations,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Otherwise, lookup chatbot class in registry and instantiate it
        chatbot_class = chatbot_registry.get_chatbot_class(model)
        if not chatbot_class:
            raise ValueError(f"Chatbot '{model}' not found in registry")

        # Instantiate the chatbot with the registry dependencies
        try:
            chatbot = chatbot_class(provider_registry, tool_manager)
        except Exception as e:
            raise ValueError(f"Failed to instantiate chatbot '{model}': {e}")

        # Override settings if provided
        if system_prompt is not None:
            chatbot.system_prompt = system_prompt
        if tool_servers is not None:
            chatbot.tool_servers = tool_servers
        if temperature is not None:
            chatbot.temperature = temperature
        if max_tokens is not None:
            chatbot.max_tokens = max_tokens
        if max_iterations is not None:
            chatbot.max_iterations = max_iterations
        
        return chatbot
