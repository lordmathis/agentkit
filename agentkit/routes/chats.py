import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agentkit.agents.manager import AgentManager

router = APIRouter()


class ModelParams(BaseModel):
    max_iterations: Optional[int] = 5
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatConfig(BaseModel):
    model: str
    system_prompt: Optional[str] = None
    tool_servers: Optional[List[str]] = None
    model_params: Optional[ModelParams] = None


class CreateChatRequest(BaseModel):
    title: Optional[str] = "Untitled Chat"
    config: ChatConfig


class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    config: Optional[ChatConfig] = None


class SendMessageRequest(BaseModel):
    message: str
    file_ids: List[str] = []
    stream: Optional[bool] = False


class BranchChatRequest(BaseModel):
    message_id: str
    title: Optional[str] = None


class EditLastMessageRequest(BaseModel):
    message: str


@router.post("/chats")
async def create_chat(request: Request, body: CreateChatRequest):
    """
    Create a new chat session with an agent.
    """
    database = request.app.state.database
    agent_manager: AgentManager = request.app.state.agent_manager

    chat = database.create_chat(title=body.title)

    try:
        agent_manager.create(
            chat_id=chat.id,
            config=body.config.model_dump(),
        )
    except ValueError as e:
        database.delete_chat(chat.id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        database.delete_chat(chat.id)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

    updated_chat = database.get_chat(chat.id)

    return {
        "id": updated_chat.id,
        "title": updated_chat.title,
        "created_at": updated_chat.created_at.isoformat(),
        "updated_at": updated_chat.updated_at.isoformat(),
        "model": updated_chat.model,
        "system_prompt": updated_chat.system_prompt,
        "tool_servers": json.loads(updated_chat.tool_servers)
        if updated_chat.tool_servers
        else None,
        "model_params": json.loads(updated_chat.model_params)
        if updated_chat.model_params
        else None,
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
                "tool_servers": json.loads(chat.tool_servers)
                if chat.tool_servers
                else None,
                "model_params": json.loads(chat.model_params)
                if chat.model_params
                else None,
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
                "tool_calls": json.loads(msg.tool_calls) if msg.tool_calls else None,
                "tool_call_id": msg.tool_call_id,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat(),
                "files": [
                    {
                        "id": database.get_file(fid).id,
                        "filename": database.get_file(fid).filename,
                        "content_type": database.get_file(fid).content_type,
                    }
                    for fid in (json.loads(msg.file_ids) if msg.file_ids else [])
                    if database.get_file(fid)
                ],
            }
            for msg in messages
        ],
    }


@router.delete("/chats/{chat_id}")
async def delete_chat(request: Request, chat_id: str):
    """
    Delete a chat and all its messages, and remove its agent.
    """
    database = request.app.state.database
    agent_manager: AgentManager = request.app.state.agent_manager

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    agent_manager.remove(chat_id)

    database.delete_chat(chat_id)

    return {"success": True}


@router.patch("/chats/{chat_id}")
async def update_chat(request: Request, chat_id: str, body: UpdateChatRequest):
    """
    Update chat metadata (e.g., title) and/or configuration.
    """
    database = request.app.state.database
    agent_manager: AgentManager = request.app.state.agent_manager

    chat = database.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    update_kwargs = {}

    if body.title is not None:
        update_kwargs["title"] = body.title

    if body.config:
        update_kwargs["model"] = body.config.model
        update_kwargs["system_prompt"] = body.config.system_prompt
        update_kwargs["tool_servers"] = (
            json.dumps(body.config.tool_servers) if body.config.tool_servers else None
        )
        update_kwargs["model_params"] = (
            json.dumps(body.config.model_params.model_dump())
            if body.config.model_params
            else None
        )

        try:
            agent_manager.remove(chat_id)
            agent_manager.create(chat_id=chat_id, config=body.config.model_dump())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update agent: {str(e)}"
            )

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
        "tool_servers": json.loads(updated_chat.tool_servers)
        if updated_chat.tool_servers
        else None,
        "model_params": json.loads(updated_chat.model_params)
        if updated_chat.model_params
        else None,
    }


@router.post("/chats/{chat_id}/branch")
async def branch_chat(request: Request, chat_id: str, body: BranchChatRequest):
    """
    Create a new chat branching from an existing chat.
    Copies all messages and attachments up to and including the specified message.
    This allows exploring different conversation paths without losing the original.
    """
    database = request.app.state.database
    agent_manager: AgentManager = request.app.state.agent_manager

    source_chat = database.get_chat(chat_id)
    if not source_chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    branched_chat = database.branch_chat(
        source_chat_id=chat_id, up_to_message_id=body.message_id, new_title=body.title
    )

    if not branched_chat:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to branch chat. Message '{body.message_id}' may not exist in chat '{chat_id}'.",
        )

    try:
        config = {
            "model": branched_chat.model,
            "system_prompt": branched_chat.system_prompt,
            "tool_servers": json.loads(branched_chat.tool_servers)
            if branched_chat.tool_servers
            else None,
            "model_params": json.loads(branched_chat.model_params)
            if branched_chat.model_params
            else None,
        }

        agent_manager.create(chat_id=branched_chat.id, config=config)
    except Exception as e:
        database.delete_chat(branched_chat.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent for branch: {str(e)}",
        )

    messages = database.get_chat_history(branched_chat.id, limit=1000)

    return {
        "id": branched_chat.id,
        "title": branched_chat.title,
        "created_at": branched_chat.created_at.isoformat(),
        "updated_at": branched_chat.updated_at.isoformat(),
        "model": branched_chat.model,
        "system_prompt": branched_chat.system_prompt,
        "tool_servers": json.loads(branched_chat.tool_servers)
        if branched_chat.tool_servers
        else None,
        "model_params": json.loads(branched_chat.model_params)
        if branched_chat.model_params
        else None,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "reasoning_content": msg.reasoning_content,
                "tool_calls": json.loads(msg.tool_calls) if msg.tool_calls else None,
                "tool_call_id": msg.tool_call_id,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat(),
                "files": [
                    {
                        "id": database.get_file(fid).id,
                        "filename": database.get_file(fid).filename,
                        "content_type": database.get_file(fid).content_type,
                    }
                    for fid in (json.loads(msg.file_ids) if msg.file_ids else [])
                    if database.get_file(fid)
                ],
            }
            for msg in messages
        ],
    }


@router.post("/chats/{chat_id}/messages")
async def send_message(request: Request, chat_id: str, body: SendMessageRequest):
    """
    Send a message and get AI response.

    Supports both streaming and non-streaming responses.
    For streaming, set stream=true in request body and use Server-Sent Events (SSE).
    """
    agent_manager: AgentManager = request.app.state.agent_manager

    try:
        agent = agent_manager.get(chat_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if body.stream:
        raise HTTPException(
            status_code=501, detail="Streaming support not yet implemented"
        )

    try:
        result = await agent.chat(message=body.message, file_ids=body.file_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/chats/{chat_id}/retry")
async def retry_message(request: Request, chat_id: str):
    """
    Retry the last message by deleting the last assistant response and re-processing.

    This is useful when the LLM fails or returns an error. It resends all messages
    up to but not including the last assistant response.
    """
    agent_manager: AgentManager = request.app.state.agent_manager

    try:
        agent = agent_manager.get(chat_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = await agent.retry()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/chats/{chat_id}/edit")
async def edit_last_user_message(
    request: Request, chat_id: str, body: EditLastMessageRequest
):
    """
    Edit the last user message and delete the assistant's response, then re-process.

    This allows users to modify their last message and get a new response from the LLM.
    """
    agent_manager: AgentManager = request.app.state.agent_manager

    try:
        agent = agent_manager.get(chat_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = await agent.edit(body.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
