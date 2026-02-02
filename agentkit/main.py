import logging

import uvicorn
from dotenv import load_dotenv

from agentkit.config import AppConfig, load_config
from agentkit.server import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

if __name__ == "__main__":
    load_dotenv(override=True)
    app_config: AppConfig = load_config('config.yaml')

    # Store config in app state so lifespan can access it
    app.state.app_config = app_config

    # Run the FastAPI app with uvicorn
    uvicorn.run(
        app,
        host=app_config.server.host,
        port=app_config.server.port
    )
