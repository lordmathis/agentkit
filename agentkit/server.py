import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentkit.config import AppConfig
from agentkit.db import Database
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup: Initialize tool manager and other resources
    logger.info("Initializing application...")
    app_config: AppConfig = app.state.app_config

    # Initialize database
    logger.info("Initializing database...")
    database = Database(app_config.history_db_path)
    app.state.database = database

    # Initialize provider registry
    logger.info("Initializing provider registry...")
    provider_registry = ProviderRegistry(app_config.providers)
    app.state.provider_registry = provider_registry

    # Initialize and start tool manager
    try:
        tool_manager = ToolManager(app_config.mcps)
        await tool_manager.start()
        app.state.tool_manager = tool_manager
    except Exception as e:
        logger.error(f"Failed to start tool manager: {e}", exc_info=True)
        # Clean up already initialized resources
        database.close()
        raise

    # Initialize model registry
    logger.info("Initializing chatbot registry...")
    model_registry = ChatbotRegistry(provider_registry, tool_manager)
    app.state.model_registry = model_registry

    logger.info("Server started successfully")

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down server...")
    try:
        await tool_manager.stop()
    except Exception as e:
        logger.error(f"Error during tool manager shutdown: {e}", exc_info=True)
    
    try:
        database.close()
    except Exception as e:
        logger.error(f"Error during database shutdown: {e}", exc_info=True)
    
    logger.info("Server shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
