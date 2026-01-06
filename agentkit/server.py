from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentkit.config import AppConfig
from agentkit.db import Database
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager
from agentkit.routes import register_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup: Initialize tool manager and other resources
    app_config: AppConfig = app.state.app_config

    # Initialize database
    database = Database(app_config.history_db_path)
    app.state.database = database

    # Initialize provider registry
    provider_registry = ProviderRegistry(app_config.providers)
    app.state.provider_registry = provider_registry

    # Initialize and start tool manager
    tool_manager = ToolManager(app_config.mcps)
    await tool_manager.start()
    app.state.tool_manager = tool_manager

    # Initialize model registry
    chatbot_registry = ChatbotRegistry(provider_registry, tool_manager)
    app.state.model_registry = chatbot_registry

    print("Server started successfully")

    yield

    # Shutdown: Clean up resources
    print("Shutting down server...")
    await tool_manager.stop()
    database.close()
    print("Server shutdown complete")


app = FastAPI(lifespan=lifespan)

# Add CORS middleware for web UI development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
register_routes(app)
