
from fastapi import FastAPI
from agentkit.models import ModelRegistry

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models():
    models = ModelRegistry.list_models()
    return {
        "object": "list",
        "data": [{"id": model_name, "object": "model", "owned_by": "agentkit"} for model_name in models]
    }

