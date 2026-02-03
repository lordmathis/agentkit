import os
import tempfile
import time

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

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


@router.get("/config/default-chat")
async def get_default_chat_config(request: Request):
    """
    Get default chat configuration from the app config.
    """
    app_config = request.app.state.app_config
    default_chat = app_config.default_chat

    # Build the full model identifier if both provider and model are specified
    model = None
    if default_chat.provider_id and default_chat.model_id:
        model = f"{default_chat.provider_id}:{default_chat.model_id}"
    elif default_chat.model_id:
        model = default_chat.model_id

    return {
        "model": model,
        "system_prompt": default_chat.system_prompt,
        "tool_servers": default_chat.tool_servers or [],
        "model_params": {
            "max_iterations": default_chat.max_iterations,
            "temperature": default_chat.temperature,
            "max_tokens": default_chat.max_tokens,
        }
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

@router.post("/transcribe")
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """
    Transcribe an audio file using the configured ASR service.
    """
    transcription_cfg = request.app.state.app_config.transcription
    
    # Check if transcription service is configured
    if not transcription_cfg.base_url:
        raise HTTPException(
            status_code=503,
            detail="Transcription service not configured. Please set transcription.base_url in config.yaml"
        )
    
    # Read the audio file
    try:
        audio_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {str(e)}")
    
    # Save to temporary file (required for multipart upload)
    temp_file = None
    try:
        # Create temporary file with original filename extension
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        temp_file.write(audio_content)
        temp_file.close()
        
        files = {
            "file": (file.filename, open(temp_file.name, "rb"), file.content_type)
        }
        
        data = {
            "model": transcription_cfg.model,
        }
        headers = {}
        if transcription_cfg.api_key:
            headers["Authorization"] = f"Bearer {transcription_cfg.api_key}"
        
        # Make request to the transcription service
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{transcription_cfg.base_url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=300.0
                )
                
                # Close the file handle
                files["file"][1].close()
                
                # Check response status
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Transcription service error: {response.text}"
                    )
                
                # Return the transcription result
                return response.json()
                    
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="Transcription service timeout"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to transcription service: {str(e)}"
                )
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass
