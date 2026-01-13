import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agentkit.config import AppConfig
from agentkit.db import Database
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager
from agentkit.services.chat_service import ChatServiceManager
from agentkit.routes import register_routes

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
        tool_manager = ToolManager(
            app_config.mcps,
            app_config.mcp_timeout,
            app_config.plugins.agents_dir
        )
        await tool_manager.start()
        app.state.tool_manager = tool_manager
    except Exception as e:
        logger.error(f"Failed to start tool manager: {e}", exc_info=True)
        # Clean up already initialized resources
        database.close()
        raise

    # Initialize model registry
    logger.info("Initializing chatbot registry...")
    model_registry = ChatbotRegistry(
        provider_registry, 
        tool_manager,
        app_config.plugins.chatbots_dir
    )
    app.state.model_registry = model_registry

    # Initialize chat service manager
    logger.info("Initializing chat service manager...")
    chat_service_manager = ChatServiceManager(
        db=database,
        provider_registry=provider_registry,
        chatbot_registry=model_registry,
        tool_manager=tool_manager
    )
    app.state.chat_service_manager = chat_service_manager

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

# Configure CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port and common dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
register_routes(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Serve static files from the web UI build (production)
webui_dist = Path(__file__).parent.parent / "webui" / "dist"
if webui_dist.exists():
    app.mount("/assets", StaticFiles(directory=webui_dist / "assets"), name="assets")
    
    def _serve_with_compression(file_path: Path, request: Request, content_type: str | None = None) -> FileResponse:
        """Serve a file with compression support (brotli/gzip)"""
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_brotli = "br" in accept_encoding.lower()
        supports_gzip = "gzip" in accept_encoding.lower()
        
        if content_type is None:
            content_type = _get_content_type(file_path)
        
        # Check for brotli version first (better compression)
        if supports_brotli:
            br_path = Path(str(file_path) + ".br")
            if br_path.exists():
                return FileResponse(
                    br_path,
                    headers={
                        "Content-Encoding": "br",
                        "Content-Type": content_type
                    }
                )
        
        # Fall back to gzip
        if supports_gzip:
            gz_path = Path(str(file_path) + ".gz")
            if gz_path.exists():
                return FileResponse(
                    gz_path,
                    headers={
                        "Content-Encoding": "gzip",
                        "Content-Type": content_type
                    }
                )
        
        # Serve uncompressed
        return FileResponse(file_path)
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        """Serve the SPA for all non-API routes with brotli/gzip support"""
        # If requesting a specific file that exists, serve it
        file_path = webui_dist / full_path
        if file_path.exists() and file_path.is_file():
            return _serve_with_compression(file_path, request)
        
        # Otherwise serve index.html (SPA routing)
        index_path = webui_dist / "index.html"
        return _serve_with_compression(index_path, request, "text/html")
else:
    logger.warning(f"Web UI build not found at {webui_dist}. Run 'cd webui && npm run build' to build the frontend.")


def _get_content_type(file_path: Path) -> str:
    """Get MIME type for a file based on its extension"""
    suffix = file_path.suffix.lower()
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
    }
    return content_types.get(suffix, "application/octet-stream")

