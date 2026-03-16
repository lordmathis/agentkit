from fastapi import FastAPI

from agentkit.routes import (
    approvals,
    chats,
    config,
    repo_browser,
    media,
    skills,
    tools,
    files,
)


def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI application."""
    prefix = "/api"
    app.include_router(approvals.router, prefix=prefix, tags=["approvals"])
    app.include_router(chats.router, prefix=prefix, tags=["chats"])
    app.include_router(config.router, prefix=prefix, tags=["config"])
    app.include_router(repo_browser.router, prefix=prefix, tags=["repo_browser"])
    app.include_router(files.router, prefix=prefix, tags=["files"])
    app.include_router(media.router, prefix=prefix, tags=["media"])
    app.include_router(skills.router, prefix=prefix, tags=["skills"])
    app.include_router(tools.router, prefix=prefix, tags=["tools"])
