from fastapi import FastAPI
from agentkit.routes import models, chats


def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI application."""
    prefix = "/api"
    app.include_router(models.router, prefix=prefix, tags=["models"])
    app.include_router(chats.router, prefix=prefix, tags=["chats"])