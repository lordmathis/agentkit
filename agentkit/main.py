import signal
import sys

from dotenv import load_dotenv

from agentkit.agents import AgentRegistry
from agentkit.config import AppConfig, load_config
from agentkit.db import Database
from agentkit.mcps import MCPManager
from agentkit.models.registry import ModelRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.server import app

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    database = Database(app_config.history_db_path)

    provider_registry = ProviderRegistry(app_config.providers)
    mcp_manager = MCPManager(app_config.mcps)

    agent_registry = AgentRegistry(provider_registry, mcp_manager)
    model_registry = ModelRegistry(provider_registry, agent_registry, mcp_manager)

    app.state.database = database
    app.state.provider_registry = provider_registry
    app.state.mcp_manager = mcp_manager
    app.state.agent_registry = agent_registry
    app.state.model_registry = model_registry

    cleanup_state = {"done": False}

    def cleanup():
        """Clean up resources on shutdown"""
        if cleanup_state["done"]:
            return
        cleanup_state["done"] = True
        print("\nShutting down...")
        database.close()
        mcp_manager.close_all()

    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        cleanup()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Mount web ui app


        import uvicorn
        uvicorn.run(app, host=app_config.server.host, port=app_config.server.port)
    finally:
        cleanup()
