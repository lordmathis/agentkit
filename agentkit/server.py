
import time
from fastapi import FastAPI
from agentkit.registry import PluginRegistry

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models():
    agents = PluginRegistry.list_plugins()
    return {
        "object": "list",
        "data": [{"id": agent_name, "object": "model", "owned_by": "agentkit"} for agent_name in agents]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    model_name = request.get("model")
    if not model_name:
        return {"error": "Model name is required."}

    agent = PluginRegistry.get_plugin(model_name)
    if agent is None:
        return {"error": f"Model {model_name} not found."}

    messages = request.get("messages", [])
    response_text = agent.chat(messages)

    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": time.time(),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
    }
