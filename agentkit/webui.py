import gradio as gr
from gradio import themes
from gradio.themes.utils import colors, sizes
from typing import List, Dict, Any
from agentkit.models import ModelRegistry


# Create Cyberpunk 2077 inspired theme using Gradio's theme builder
cyberpunk_theme = themes.Base(
    primary_hue=colors.yellow,
    secondary_hue=colors.cyan,
    neutral_hue=colors.slate,
    radius_size=sizes.radius_sm,
).set(
    body_background_fill='*neutral_950',
    body_background_fill_dark='*neutral_950',

    # Primary button (yellow/gold like CP2077)
    button_primary_background_fill='*primary_500',
    button_primary_background_fill_hover='*primary_400',
    button_primary_text_color='*neutral_950',
    button_primary_border_color='*primary_500',

    # Secondary buttons (cyan accents)
    button_secondary_background_fill='*neutral_800',
    button_secondary_background_fill_hover='*neutral_700',
    button_secondary_text_color='*secondary_400',
    button_secondary_border_color='*secondary_500',

    # Input fields
    input_background_fill='*neutral_900',
    input_background_fill_dark='*neutral_900',
    input_border_color='*secondary_500',
    input_border_color_focus='*primary_500',

    # Panels and containers
    panel_background_fill='*neutral_900',
    panel_background_fill_dark='*neutral_900',
    panel_border_color='*secondary_600',

    background_fill_primary='*neutral_900',
    background_fill_primary_dark='*neutral_900',
    background_fill_secondary='*neutral_800',
    background_fill_secondary_dark='*neutral_800',

    # Border colors
    border_color_primary='*secondary_500',
    border_color_primary_dark='*secondary_500',

    # Text colors
    body_text_color='*secondary_200',
    body_text_color_subdued='*secondary_400',
    block_label_text_color='*primary_400',
    block_title_text_color='*primary_400',
)


def create_ui() -> gr.Blocks:
    """Create and return the Gradio interface."""

    with gr.Blocks(title="⚡ AGENTKIT NEURAL INTERFACE", theme=cyberpunk_theme) as demo:
        gr.Markdown("# ⚡ AGENTKIT NEURAL INTERFACE ⚡")

        with gr.Row():
            model_dropdown = gr.Dropdown(
                label="Select Model",
                choices=[],
                value=None,
                interactive=True,
                scale=3
            )
            refresh_btn = gr.Button("🔄 Refresh Models", scale=1)

        chatbot = gr.Chatbot(
            label="Chat",
            height=500
        )

        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Type your message here...",
                lines=2,
                scale=4
            )
            send_btn = gr.Button("Send", scale=1, variant="primary")

        clear_btn = gr.Button("Clear Chat")

        def load_models():
            """Load available models."""
            models = list(ModelRegistry.list_models().keys())
            return gr.Dropdown(choices=models, value=models[0] if models else None)

        def respond(message: str, chat_history: List[Dict[str, Any]], model_name: str):
            """Handle chat response."""
            if not message.strip():
                return chat_history, ""

            if not model_name:
                chat_history.append({"role": "assistant", "content": "Please select a model first."})
                return chat_history, ""

            model = ModelRegistry.get_model(model_name)
            if model is None:
                chat_history.append({"role": "assistant", "content": f"Model {model_name} not found."})
                return chat_history, ""

            # Convert Gradio's message format to OpenAI format
            messages = []
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": message})

            # Get response from model
            try:
                response = model.chat(messages)
                # Extract content from OpenAI chat completion format
                if isinstance(response, dict) and "choices" in response:
                    choices = response.get("choices", [])
                    if choices and isinstance(choices, list):
                        msg_dict = choices[0].get("message", {})
                        bot_response = msg_dict.get("content", str(response))
                    else:
                        bot_response = str(response)
                else:
                    bot_response = str(response)
            except Exception as e:
                bot_response = f"Error: {str(e)}"

            # Add user message
            chat_history.append({"role": "user", "content": message})
            # Add bot response
            chat_history.append({"role": "assistant", "content": bot_response})

            return chat_history, ""

        def clear_chat():
            """Clear the chat history."""
            return []

        # Event handlers
        demo.load(load_models, outputs=model_dropdown)
        refresh_btn.click(load_models, outputs=model_dropdown)

        msg.submit(respond, inputs=[msg, chatbot, model_dropdown], outputs=[chatbot, msg])
        send_btn.click(respond, inputs=[msg, chatbot, model_dropdown], outputs=[chatbot, msg])
        clear_btn.click(clear_chat, outputs=chatbot)

    return demo
