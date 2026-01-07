from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/models")
async def list_models(request: Request):
    """
    List all available models in OpenAI-compatible format.

    Returns both predefined chatbots from the registry and provider models.
    Format: {chatbot_name} for predefined chatbots, {provider}:{model_id} for provider models.
    """
    chatbot_registry = request.app.state.model_registry
    provider_registry = request.app.state.provider_registry

    models = []

    # Add predefined chatbots from registry
    chatbot_models = chatbot_registry.list_models()
    for model_name in chatbot_models:
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

    return {
        "object": "list",
        "data": models
    }


@router.get("/chatbots")
async def list_chatbots(request: Request):
    """
    List all predefined chatbots from the registry with their configurations.
    """
    chatbot_registry = request.app.state.model_registry

    chatbots = []
    model_names = chatbot_registry.list_models()

    for model_name in model_names:
        chatbot = chatbot_registry.get_model(model_name)
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
                    # MCP tools have parameters attribute
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                elif hasattr(tool, 'inputs'):
                    # SMOLAGENTS tools have inputs attribute
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputs
                    }
                else:
                    tool_dict = {
                        "name": getattr(tool, 'name', 'unknown'),
                        "description": getattr(tool, 'description', ''),
                        "parameters": {}
                    }
                tool_list.append(tool_dict)

            # Get the actual server type from the tool manager
            server_type_enum = tool_manager.get_server_type(server_name)
            server_type = server_type_enum.value

            tool_servers.append({
                "name": server_name,
                "type": server_type,
                "tools": tool_list
            })
        except Exception as e:
            print(f"Warning: Could not list tools from server {server_name}: {e}")
            continue

    return {
        "tool_servers": tool_servers
    }
