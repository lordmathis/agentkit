from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from agentkit.services.chat_service import ChatService, ChatConfig
from agentkit.server import app

router = APIRouter()


class CreateChatRequest(BaseModel):
    title: Optional[str] = "Untitled Chat"


class UpdateChatRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    message: str
    config: ChatConfig
    stream: Optional[bool] = False


@router.post("/chats")
async def create_chat(request: Request, body: CreateChatRequest):
    """
    Create a new chat session.
    """
    database = request.app.state.database

    chat = database.create_chat(title=body.title)

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
    Delete a chat and all its messages.
    """
    database = request.app.state.database

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

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
    database = request.app.state.database
    provider_registry = request.app.state.provider_registry
    chatbot_registry = request.app.state.model_registry
    tool_manager = request.app.state.tool_manager

    # Verify chat exists
    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    # Create chat service
    chat_service = ChatService(
        db=database,
        provider_registry=provider_registry,
        chatbot_registry=chatbot_registry,
        tool_manager=tool_manager
    )

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
            result = await chat_service.send_message(
                chat_id=chat_id,
                message=body.message,
                config=body.config
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
