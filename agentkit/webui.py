import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)


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


def _serve_with_compression(
    file_path: Path, request: Request, content_type: str | None = None
) -> FileResponse:
    """Serve a file with compression support (brotli/gzip)"""
    logger.debug(f"Attempting to serve file: {file_path}")
    accept_encoding = request.headers.get("accept-encoding", "")
    supports_brotli = "br" in accept_encoding.lower()
    supports_gzip = "gzip" in accept_encoding.lower()

    if content_type is None:
        content_type = _get_content_type(file_path)

    # Check for brotli version first (better compression)
    if supports_brotli:
        br_path = Path(str(file_path) + ".br")
        if br_path.exists():
            logger.info(f"Serving brotli compressed file: {br_path}")
            return FileResponse(
                br_path,
                headers={"Content-Encoding": "br", "Content-Type": content_type},
            )

    # Fall back to gzip
    if supports_gzip:
        gz_path = Path(str(file_path) + ".gz")
        if gz_path.exists():
            logger.info(f"Serving gzip compressed file: {gz_path}")
            return FileResponse(
                gz_path,
                headers={"Content-Encoding": "gzip", "Content-Type": content_type},
            )

    # Serve uncompressed
    return FileResponse(file_path)


def setup_webui(app: FastAPI):
    """Register routes to serve the Web UI"""
    webui_dist = Path(__file__).parent.parent / "webui" / "dist"

    if not webui_dist.exists():
        logger.warning(
            f"Web UI build not found at {webui_dist}. Run 'cd webui && npm run build' to build the frontend."
        )
        return

    @app.get("/{full_path:path}")
    async def serve_static(full_path: str, request: Request):
        """Serve static files with compression support"""
        # Serve index.html on root
        if not full_path:
            index_path = webui_dist / "index.html"
            return _serve_with_compression(index_path, request, "text/html")

        file_path = webui_dist / full_path
        if file_path.exists() and file_path.is_file():
            return _serve_with_compression(file_path, request)

        # For SPA routing, serve index.html for non-existent paths that don't look like files
        if "." not in full_path:
            index_path = webui_dist / "index.html"
            return _serve_with_compression(index_path, request, "text/html")

        raise HTTPException(status_code=404, detail="File not found")
