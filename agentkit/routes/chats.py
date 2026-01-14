from fastapi import APIRouter, Request, HTTPException, UploadFile
from pydantic import BaseModel
from typing import List, Optional
import json
import os

from agentkit.services.chat_service import ChatServiceManager, ChatConfig

router = APIRouter()


class CreateChatRequest(BaseModel):
    title: Optional[str] = "Untitled Chat"
    config: ChatConfig  # Chat configuration is required at creation time


class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    config: Optional[ChatConfig] = None


class SendMessageRequest(BaseModel):
    message: str
    stream: Optional[bool] = False  # Config is now set at chat creation time


@router.post("/chats")
async def create_chat(request: Request, body: CreateChatRequest):
    """
    Create a new chat session with a ChatService.
    """
    database = request.app.state.database
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    # Create chat in database
    chat = database.create_chat(title=body.title)

    # Create chat service with chatbot
    try:
        chat_service_manager.create_chat_service(
            chat_id=chat.id,
            config=body.config
        )
    except ValueError as e:
        # If chat service creation fails, clean up the chat
        database.delete_chat(chat.id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # If chat service creation fails, clean up the chat
        database.delete_chat(chat.id)
        raise HTTPException(status_code=500, detail=f"Failed to create chat service: {str(e)}")

    # Retrieve updated chat with config
    updated_chat = database.get_chat(chat.id)
    
    return {
        "id": updated_chat.id,
        "title": updated_chat.title,
        "created_at": updated_chat.created_at.isoformat(),
        "updated_at": updated_chat.updated_at.isoformat(),
        "model": updated_chat.model,
        "system_prompt": updated_chat.system_prompt,
        "tool_servers": json.loads(updated_chat.tool_servers) if updated_chat.tool_servers else None,
        "model_params": json.loads(updated_chat.model_params) if updated_chat.model_params else None,
    }


@router.get("/chats")
async def list_chats(request: Request, limit: int = 20):
    """
    List recent chats ordered by most recently updated.
    """
    database = request.app.state.database

    chats = database.list_chats(limit=limit)

    return {
        "chats": [
            {
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
                "model": chat.model,
                "system_prompt": chat.system_prompt,
                "tool_servers": json.loads(chat.tool_servers) if chat.tool_servers else None,
                "model_params": json.loads(chat.model_params) if chat.model_params else None,
            }
            for chat in chats
        ]
    }


@router.get("/chats/{chat_id}")
async def get_chat(request: Request, chat_id: str):
    """
    Get chat metadata and full message history.
    """
    database = request.app.state.database

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    messages = database.get_chat_history(chat_id, limit=1000)

    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "model": chat.model,
        "system_prompt": chat.system_prompt,
        "tool_servers": json.loads(chat.tool_servers) if chat.tool_servers else None,
        "model_params": json.loads(chat.model_params) if chat.model_params else None,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "reasoning_content": msg.reasoning_content,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat(),
                "files": [
                    {
                        "id": file.id,
                        "filename": file.filename,
                        "content_type": file.content_type,
                    }
                    for file in database.get_message_attachments(msg.id)
                ]
            }
            for msg in messages
        ]
    }


@router.delete("/chats/{chat_id}")
async def delete_chat(request: Request, chat_id: str):
    """
    Delete a chat and all its messages, and remove its chat service.
    """
    database = request.app.state.database
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    # Remove chat service
    chat_service_manager.remove_chat_service(chat_id)

    # Delete from database
    database.delete_chat(chat_id)

    return {
        "success": True
    }


@router.patch("/chats/{chat_id}")
async def update_chat(request: Request, chat_id: str, body: UpdateChatRequest):
    """
    Update chat metadata (e.g., title) and/or configuration.
    """
    database = request.app.state.database
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    # Prepare update kwargs
    update_kwargs = {}
    
    if body.title is not None:
        update_kwargs["title"] = body.title
    
    # Update configuration if provided
    if body.config:
        update_kwargs["model"] = body.config.model
        update_kwargs["system_prompt"] = body.config.system_prompt
        update_kwargs["tool_servers"] = json.dumps(body.config.tool_servers) if body.config.tool_servers else None
        update_kwargs["model_params"] = json.dumps(body.config.model_params) if body.config.model_params else None
        
        # Recreate chat service with new config
        try:
            chat_service_manager.remove_chat_service(chat_id)
            chat_service_manager.create_chat_service(
                chat_id=chat_id,
                config=body.config
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update chat service: {str(e)}")

    # Update database
    updated_chat = database.update_chat(chat_id, **update_kwargs)
    if not updated_chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    return {
        "id": updated_chat.id,
        "title": updated_chat.title,
        "created_at": updated_chat.created_at.isoformat(),
        "updated_at": updated_chat.updated_at.isoformat(),
        "model": updated_chat.model,
        "system_prompt": updated_chat.system_prompt,
        "tool_servers": json.loads(updated_chat.tool_servers) if updated_chat.tool_servers else None,
        "model_params": json.loads(updated_chat.model_params) if updated_chat.model_params else None,
    }


@router.post("/chats/{chat_id}/messages")
async def send_message(request: Request, chat_id: str, body: SendMessageRequest):
    """
    Send a message and get AI response.

    Supports both streaming and non-streaming responses.
    For streaming, set stream=true in request body and use Server-Sent Events (SSE).
    """
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    try:
        chat_service = chat_service_manager.get_or_create_chat_service(chat_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if body.stream:
        # TODO: Implement streaming support
        # For now, return error
        raise HTTPException(
            status_code=501,
            detail="Streaming support not yet implemented"
        )
    else:
        # Non-streaming response
        try:
            result = await chat_service.send_message(message=body.message)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/chats/{chat_id}/files")
async def upload_files(request: Request, files: List[UploadFile], chat_id: str):
    """
    Upload a file to be used in the chat session.
    """
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    try:
        chat_service = chat_service_manager.get_or_create_chat_service(chat_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    file_locations = []
    content_types = []

    uploads_dir = f"{request.app.state.app_config.uploads_dir}/{chat_id}"
    os.makedirs(uploads_dir, exist_ok=True)

    for file in files:
        file_location = f"{uploads_dir}/{file.filename}"
        with open(file_location, "wb") as file_object:
            file_object.write(await file.read())
        file_locations.append(file_location)
        content_types.append(file.content_type)

    # Handle file in chat service
    try:
        for file_location, content_type in zip(file_locations, content_types):
            await chat_service.handle_file_upload(file_location, content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle file upload: {str(e)}")

    return {
        "filenames": [file.filename for file in files]
    }