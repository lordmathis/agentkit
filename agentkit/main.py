import os

import gradio as gr
from dotenv import load_dotenv

from agentkit.agents.registry import AgentRegistry
from agentkit.config import AppConfig, load_config
from agentkit.conversation_db import get_connection
from agentkit.mcps import MCPManager
from agentkit.models.registry import ModelRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.server import app
from agentkit.webui import create_ui

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    conn = get_connection(app_config.conversation_db_path)

    MCPManager.configure(app_config.mcps)
    ProviderRegistry.register_all(app_config.providers)
    AgentRegistry.register_all()
    ModelRegistry.register_all()

    try:
        demo = create_ui()
        gr.mount_gradio_app(app, demo, path="/")

        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        MCPManager.close_all()