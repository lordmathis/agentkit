import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mikoshi.lifespan import lifespan
from mikoshi.middleware import InFlightMiddleware, InFlightRequests
from mikoshi.routes import register_routes
from mikoshi.webui import setup_webui

logger = logging.getLogger(__name__)

in_flight = InFlightRequests()

app = FastAPI(lifespan=lifespan)
app.state.in_flight = in_flight

app.add_middleware(InFlightMiddleware, tracker=in_flight)

# Configure CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],  # Vite default port and common dev port
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
setup_webui(app)
