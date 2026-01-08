from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from agentkit.services.chat_service import ChatServiceManager, ChatConfig

router = APIRouter()


class CreateChatRequest(BaseModel):
    title: Optional[str] = "Untitled Chat"
    config: ChatConfig  # Chat configuration is required at creation time


class UpdateChatRequest(BaseModel):
    title: str


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

    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat()
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
                "system_prompt": chat.system_prompt
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
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat()
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
    Update chat metadata (e.g., title).
    """
    database = request.app.state.database

    chat = database.update_chat(chat_id, title=body.title)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat()
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
