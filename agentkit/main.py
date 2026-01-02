import os

import gradio as gr
from dotenv import load_dotenv

from agentkit.agents import AgentRegistry
from agentkit.config import AppConfig, load_config
from agentkit.mcps import MCPManager
from agentkit.models.registry import ModelRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.server import app
from agentkit.history import ChatHistory
from agentkit.webui import create_ui
from agentkit.server import app

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    chat_history = ChatHistory(app_config.history_db_path)

    provider_registry = ProviderRegistry(app_config.providers)
    mcp_manager = MCPManager(app_config.mcps)

    agent_registry = AgentRegistry()
    model_registry = ModelRegistry()

    app.state.chat_history = chat_history
    app.state.provider_registry = provider_registry
    app.state.mcp_manager = mcp_manager
    app.state.agent_registry = agent_registry
    app.state.model_registry = model_registry

    


    try:
        demo = create_ui()
        gr.mount_gradio_app(app, demo, path="/")

        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        mcp_manager.close_all()