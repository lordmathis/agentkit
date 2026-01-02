import gradio as gr
from gradio import themes
from gradio.themes.utils import colors, sizes
from typing import List, Dict, Any
from agentkit.models import ModelRegistry


def create_ui() -> gr.Blocks:
    """Create and return the Gradio interface."""

    with gr.Blocks(title="⚡ AGENTKIT NEURAL INTERFACE") as demo:
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
