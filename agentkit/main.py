import os
from dotenv import load_dotenv
import gradio as gr
from agentkit.config import AppConfig, load_config
from agentkit.mcps import MCPManager
from agentkit.server import app

from agentkit.webui import create_ui


if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    MCPManager.configure(app_config.mcps)

    try:
        demo = create_ui()
        gr.mount_gradio_app(app, demo, path="/ui")

        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        MCPManager.close_all()