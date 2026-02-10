from fastapi import FastAPI

from agentkit.routes import chats, config, github, media, skills, tools


def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI application."""
    prefix = "/api"
    app.include_router(chats.router, prefix=prefix, tags=["chats"])
    app.include_router(config.router, prefix=prefix, tags=["config"])
    app.include_router(github.router, prefix=prefix, tags=["github"])
    app.include_router(media.router, prefix=prefix, tags=["media"])
    app.include_router(skills.router, prefix=prefix, tags=["skills"])
    app.include_router(tools.router, prefix=prefix, tags=["tools"])
