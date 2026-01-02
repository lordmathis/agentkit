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
from agentkit.server import app
from agentkit.webui import create_ui

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    chat_history = ChatHistory(app_config.history_db_path)

    provider_registry = ProviderRegistry(app_config.providers)
    mcp_manager = MCPManager(app_config.mcps)

    agent_registry = AgentRegistry(provider_registry, mcp_manager)
    model_registry = ModelRegistry(provider_registry, agent_registry, mcp_manager)

    app.state.chat_history = chat_history
    app.state.provider_registry = provider_registry
    app.state.mcp_manager = mcp_manager
    app.state.agent_registry = agent_registry
    app.state.model_registry = model_registry
    app.state.chat_history = chat_history

    try:
        ui = create_ui(
            provider_registry,
            mcp_manager,
            agent_registry,
            model_registry,
            chat_history
        )
        gr.mount_gradio_app(app, ui, path="/")

        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        chat_history.close()
        mcp_manager.close_all()
