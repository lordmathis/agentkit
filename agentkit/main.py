import os
from dotenv import load_dotenv
import gradio as gr
from agentkit.config import AppConfig, load_config
from agentkit.mcp_manager import MCPManager
from agentkit.server import app
from agentkit.registry import PluginRegistry

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from agentkit.webui import create_ui

class PluginDirEventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        filepath = str(event.src_path)
        if filepath.endswith('.py') and not os.path.basename(filepath).startswith('_'):
            PluginRegistry.register_plugin(filepath)

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    MCPManager.configure(app_config.mcps)
    PluginRegistry.discover_plugins(app_config.server.plugins_dir)

    observer = Observer()
    event_handler = PluginDirEventHandler()
    observer.schedule(event_handler, app_config.server.plugins_dir, recursive=True)
    observer.start()

    try:
        demo = create_ui()
        gr.mount_gradio_app(app, demo, path="/ui")

        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        observer.stop()
        observer.join()
        MCPManager.close_all()