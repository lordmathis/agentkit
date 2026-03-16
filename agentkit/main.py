import argparse
import logging
import logging.handlers
import os
import signal
import sys
import threading

import uvicorn
from dotenv import load_dotenv
from watchfiles import watch

from agentkit.config import AppConfig, LoggingConfig, load_config
from agentkit.server import app


def configure_logging(cfg: LoggingConfig):
    formatter = logging.Formatter(cfg.format, datefmt=cfg.date_format)

    if cfg.target == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        # Rotating file handler: 10 MB per file, keep 5 backups
        handler = logging.handlers.RotatingFileHandler(
            cfg.target, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(cfg.level)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Override uvicorn loggers to use the same handler and format
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.propagate = False


def start_file_watcher(paths: list[str]) -> None:
    """Watch paths for changes; send SIGTERM on detection to trigger a clean exit."""
    logger = logging.getLogger(__name__)

    def _watch() -> None:
        logger.info(f"Watching for changes: {paths}")
        for changes in watch(*paths, raise_interrupt=False):
            changed = [path for _, path in changes]
            logger.info(f"Change detected in {changed}, shutting down for restart...")
            os.kill(os.getpid(), signal.SIGTERM)
            return  # one signal is enough

    thread = threading.Thread(target=_watch, daemon=True, name="file-watcher")
    thread.start()


if __name__ == "__main__":
    load_dotenv(override=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Exit on plugin/config changes (for use with Docker restart policy)",
    )
    args = parser.parse_args()

    app_config: AppConfig = load_config("config.yaml")
    configure_logging(app_config.logging)
    app.state.app_config = app_config

    if args.watch:
        watch_paths = [
            "config.yaml",
            app_config.plugins.agents_dir,
            app_config.plugins.tools_dir,
            app_config.plugins.skills_dir,
        ]
        start_file_watcher([p for p in watch_paths if os.path.exists(p)])

    # Run the FastAPI app with uvicorn; SIGTERM triggers graceful shutdown + lifespan teardown
    uvicorn.run(
        app, host=app_config.server.host, port=app_config.server.port, log_config=None
    )
