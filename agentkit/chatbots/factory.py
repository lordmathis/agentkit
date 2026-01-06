from typing import List, Optional

from agentkit.chatbots.chatbot import BaseChatbot
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
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_iterations: int = 5,
    ) -> BaseChatbot:
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
            return BaseChatbot(
                system_prompt=system_prompt or "",
                provider_cfg=provider.config,
                model_id=model_id,
                tool_manager=tool_manager,
                tool_servers=tool_servers or [],
                max_iterations=max_iterations,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Otherwise, lookup in chatbot registry
        chatbot = chatbot_registry.get_model(model)
        if not chatbot:
            raise ValueError(f"Chatbot '{model}' not found in registry")

        # Clone the chatbot with overridden settings
        # Note: We create a new instance to avoid mutating the registered chatbot
        return BaseChatbot(
            system_prompt=system_prompt or chatbot.system_prompt,
            provider_cfg=chatbot.provider_cfg,
            model_id=chatbot.model_id,
            tool_manager=tool_manager,
            tool_servers=tool_servers if tool_servers is not None else chatbot.tool_servers,
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
        )
