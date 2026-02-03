from fastapi import FastAPI

from agentkit.routes import chats, github, models, skills


def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI application."""
    prefix = "/api"
    app.include_router(models.router, prefix=prefix, tags=["models"])
    app.include_router(chats.router, prefix=prefix, tags=["chats"])
    app.include_router(github.router, prefix=prefix, tags=["github"])
    app.include_router(skills.router, prefix=prefix, tags=["skills"])
