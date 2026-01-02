from sqlite3 import Connection
from typing import Any, Dict, List

import gradio as gr

from agentkit.conversation_db import (create_conversation, get_conversation,
                                      get_conversation_messages,
                                      list_conversations,
                                      save_conversation_messages)
from agentkit.models import ModelRegistry


def create_ui(conn: Connection) -> gr.Blocks:
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

        def load_models():
            """Load available models."""
            models = list(ModelRegistry.list_models().keys())
            return gr.Dropdown(choices=models, value=models[0] if models else None)
        
        def load_conversations():
            """Load existing conversations from the database."""
            conversations = list_conversations(conn)
            return conversations

        def load_messages(conversation_id: str):
            """Load messages for a given conversation."""
            conversation = get_conversation(conn, conversation_id)
            if conversation is None:
                return []
            messages = get_conversation_messages(conn, conversation_id)
            chat_history = [{"role": role, "content": content} for _, role, content, _ in messages]
            return chat_history
        
        def new_conversation():
            """Start a new conversation."""
            conversation_id = create_conversation(conn, "New Conversation")
            return conversation_id, []

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
        msg.submit(respond, inputs=[msg, chatbot, model_dropdown], outputs=[chatbot, msg])
        send_btn.click(respond, inputs=[msg, chatbot, model_dropdown], outputs=[chatbot, msg])

    return demo
