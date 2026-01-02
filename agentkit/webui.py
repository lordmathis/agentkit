import gradio as gr


def create_ui(
    provider_registry,
    mcp_manager,
    agent_registry,
    model_registry,
    chat_history
):
    """Create and return a Gradio ChatInterface UI.

    Args:
        provider_registry: Registry of LLM providers
        mcp_manager: Manager for MCP servers
        agent_registry: Registry of available agents
        model_registry: Registry of available models
        chat_history: Chat history manager

    Returns:
        Gradio Blocks interface
    """

    def chat_fn(message, history):
        """Chat function for Gradio ChatInterface.

        Args:
            message: User's message string
            history: List of message dicts with 'role' and 'content'

        Returns:
            Assistant's response string
        """
        # Convert Gradio history format to OpenAI message format
        messages = []

        # In newer Gradio versions, history is already in message dict format
        if history and isinstance(history[0], dict):
            messages = history.copy()
        # Older format: list of [user_msg, assistant_msg] pairs
        elif history and isinstance(history[0], (list, tuple)):
            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": assistant_msg})

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            # Get the assistant model (you can make this configurable)
            model = model_registry.get_model("assistant")

            if model is None:
                return "Error: Assistant model not found in registry"

            # Get response from model
            response = model.chat(messages)

            # Extract the assistant's reply
            assistant_reply = response["choices"][0]["message"]["content"]

            return assistant_reply

        except Exception as e:
            return f"Error: {str(e)}"

    # Create ChatInterface
    interface = gr.ChatInterface(
        fn=chat_fn,
        title="AgentKit Assistant",
        description="Chat with the AI assistant. It can use various agents to help you with tasks.",
    )

    return interface
