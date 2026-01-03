
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/models")
async def list_models():
    app_models = app.state.model_registry.list_models().keys()
    models = [{"id": model_name, "object": "model", "owned_by": "agentkit"} for model_name in app_models]

    for provider_name, provider in app.state.provider_registry.list_providers().items():
        provider_models = provider.list_models().keys()
        models.extend(
            [{"id": model_name, "object": "model", "owned_by": provider_name} for model_name in provider_models]
        )

    return {
        "object": "list",
        "data": models
    }

