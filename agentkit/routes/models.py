from fastapi import APIRouter, Request
import time

router = APIRouter()

# Cache for models list (TTL: 5 minutes)
_models_cache = None
_models_cache_time = 0
MODELS_CACHE_TTL = 300  # 5 minutes


@router.get("/models")
async def list_models(request: Request):
    """
    List all available models in OpenAI-compatible format.

    Returns both predefined chatbots from the registry and provider models.
    Format: {chatbot_name} for predefined chatbots, {provider}:{model_id} for provider models.
    """
    global _models_cache, _models_cache_time
    
    # Return cached models if still valid
    current_time = time.time()
    if _models_cache is not None and (current_time - _models_cache_time) < MODELS_CACHE_TTL:
        return _models_cache
    
    chatbot_registry = request.app.state.model_registry
    provider_registry = request.app.state.provider_registry

    models = []

    # Add predefined chatbots from registry
    chatbot_names = chatbot_registry.list_chatbots()
    for model_name in chatbot_names:
        models.append({
            "id": model_name,
            "object": "model",
            "created": 1234567890,
            "owned_by": "agentkit"
        })

    # Add provider models
    for provider_name, provider in provider_registry.list_providers().items():
        try:
            model_ids = provider.get_model_ids()
            if model_ids:
                for model_id in model_ids:
                    models.append({
                        "id": f"{provider_name}:{model_id}",
                        "object": "model",
                        "created": 1234567890,
                        "owned_by": provider_name
                    })
        except Exception as e:
            # If a provider doesn't support listing models, skip it
            import traceback
            print(f"Warning: Could not list models from provider {provider_name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            continue

    result = {
        "object": "list",
        "data": models
    }
    
    # Cache the result
    _models_cache = result
    _models_cache_time = current_time
    
    return result


@router.get("/chatbots")
async def list_chatbots(request: Request):
    """
    List all predefined chatbots from the registry with their configurations.
    """
    chatbot_registry = request.app.state.model_registry

    chatbots = []
    chatbot_names = chatbot_registry.list_chatbot_names()

    for model_name in chatbot_names:
        chatbot = chatbot_registry.create_chatbot(model_name)
        if chatbot:
            chatbots.append({
                "name": model_name,
                "system_prompt": chatbot.system_prompt,
                "provider": chatbot.provider_cfg.name if hasattr(chatbot.provider_cfg, 'name') else "unknown",
                "model_id": chatbot.model_id,
                "tool_servers": chatbot.tool_servers,
                "temperature": chatbot.temperature,
                "max_tokens": chatbot.max_tokens,
                "max_iterations": chatbot.max_iterations
            })

    return {
        "chatbots": chatbots
    }


@router.get("/providers")
async def list_providers(request: Request):
    """
    List all configured providers with their available models.
    """
    provider_registry = request.app.state.provider_registry

    providers = []
    for provider_name, provider in provider_registry.list_providers().items():
        try:
            model_ids = provider.get_model_ids()
            if model_ids is None:
                model_ids = []
        except Exception:
            model_ids = []

        providers.append({
            "name": provider_name,
            "api_base": provider.config.api_base,
            "models": model_ids
        })

    return {
        "providers": providers
    }


@router.get("/tools")
async def list_tools(request: Request):
    """
    List all available tool servers and their tools.
    """
    tool_manager = request.app.state.tool_manager

    tool_servers = []
    server_names = await tool_manager.list_tool_servers()

    for server_name in server_names:
        try:
            tools = await tool_manager.list_tools(server_name)

            # Convert tools to dict format
            tool_list = []
            for tool in tools:
                if hasattr(tool, 'parameters'):
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                else:
                    tool_dict = {
                        "name": getattr(tool, 'name', 'unknown'),
                        "description": getattr(tool, 'description', ''),
                        "parameters": {}
                    }
                tool_list.append(tool_dict)

            tool_servers.append({
                "name": server_name,
                "tools": tool_list
            })
        except Exception as e:
            print(f"Warning: Could not list tools from server {server_name}: {e}")
            continue

    return {
        "tool_servers": tool_servers
    }
