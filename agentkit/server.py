import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agentkit.config import AppConfig
from agentkit.db import Database
from agentkit.chatbots.registry import ChatbotRegistry
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager
from agentkit.services.manager import ChatServiceManager
from agentkit.routes import register_routes
from agentkit.github.client import GitHubClient

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
            app_config.data_dir,
            app_config.plugins.tools_dir,
            app_config.mcps,
            app_config.mcp_timeout,
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

    # Initialize GitHub client if token is configured
    github_client = None
    if app_config.github_token:
        logger.info("Initializing GitHub client...")
        try:
            github_client = GitHubClient(app_config.github_token)
            # Verify authentication
            if await github_client.authenticate():
                logger.info("GitHub client authenticated successfully")
                app.state.github_client = github_client
            else:
                logger.warning("GitHub authentication failed - GitHub features will be unavailable")
                await github_client.close()
                github_client = None
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}", exc_info=True)
            if github_client:
                await github_client.close()
            github_client = None
    else:
        logger.info("GitHub token not configured - GitHub features will be unavailable")

    # Initialize chat service manager
    logger.info("Initializing chat service manager...")
    chat_service_manager = ChatServiceManager(
        db=database,
        provider_registry=provider_registry,
        chatbot_registry=model_registry,
        tool_manager=tool_manager,
        github_client=github_client
    )
    app.state.chat_service_manager = chat_service_manager

    logger.info("Server started successfully")

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down server...")
    
    if github_client:
        try:
            await github_client.close()
        except Exception as e:
            logger.error(f"Error during GitHub client shutdown: {e}", exc_info=True)
    
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
    def _serve_with_compression(file_path: Path, request: Request, content_type: str | None = None) -> FileResponse:
        """Serve a file with compression support (brotli/gzip)"""
        logger.debug(f"Attempting to serve file: {file_path}")
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_brotli = "br" in accept_encoding.lower()
        supports_gzip = "gzip" in accept_encoding.lower()
        
        logger.debug(f"Accept-Encoding header: {accept_encoding}")
        logger.debug(f"Supports brotli: {supports_brotli}, Supports gzip: {supports_gzip}")
        
        if content_type is None:
            content_type = _get_content_type(file_path)
        
        logger.debug(f"Content-Type: {content_type}")
        
        # Check for brotli version first (better compression)
        if supports_brotli:
            br_path = Path(str(file_path) + ".br")
            logger.debug(f"Checking for brotli file: {br_path}, exists: {br_path.exists()}")
            if br_path.exists():
                logger.info(f"Serving brotli compressed file: {br_path}")
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
            logger.debug(f"Checking for gzip file: {gz_path}, exists: {gz_path.exists()}")
            if gz_path.exists():
                logger.info(f"Serving gzip compressed file: {gz_path}")
                return FileResponse(
                    gz_path,
                    headers={
                        "Content-Encoding": "gzip",
                        "Content-Type": content_type
                    }
                )
        
        # Serve uncompressed
        logger.debug(f"Serving uncompressed file: {file_path}")
        return FileResponse(file_path)
    
    @app.get("/{full_path:path}")
    async def serve_static(full_path: str, request: Request):
        """Serve static files with compression support"""
        logger.debug(f"Request for path: /{full_path}")
        
        # Serve index.html on root
        if not full_path:
            logger.debug("Serving index.html for root path")
            index_path = webui_dist / "index.html"
            return _serve_with_compression(index_path, request, "text/html")
        
        file_path = webui_dist / full_path
        logger.debug(f"Checking: {file_path}")
        
        if file_path.exists() and file_path.is_file():
            logger.debug(f"File exists, serving: {file_path}")
            return _serve_with_compression(file_path, request)
        
        logger.warning(f"File not found: {full_path}")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
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

