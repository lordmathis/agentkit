
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models():
    models = app.state.model_registry.list_models().keys()
    return {
        "object": "list",
        "data": [{"id": model_name, "object": "model", "owned_by": "agentkit"} for model_name in models]
    }

