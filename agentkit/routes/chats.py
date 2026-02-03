import json
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel

from agentkit.services.chat_service import ChatConfig, ModelParams
from agentkit.services.manager import ChatServiceManager

router = APIRouter()


class CreateChatRequest(BaseModel):
    title: Optional[str] = "Untitled Chat"
    config: ChatConfig


class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    config: Optional[ChatConfig] = None


class SendMessageRequest(BaseModel):
    message: str
    stream: Optional[bool] = False


class AddGitHubFilesRequest(BaseModel):
    repo: str
    paths: List[str]
    exclude_paths: Optional[List[str]] = []


class BranchChatRequest(BaseModel):
    message_id: str
    title: Optional[str] = None


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
        chat_service_manager.create_service(
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
                "tool_calls": json.loads(msg.tool_calls) if msg.tool_calls else None,
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
    chat_service_manager.remove_service(chat_id)

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
        update_kwargs["model_params"] = json.dumps(body.config.model_params.model_dump()) if body.config.model_params else None
        
        # Recreate chat service with new config
        try:
            chat_service_manager.remove_service(chat_id)
            chat_service_manager.create_service(
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


@router.post("/chats/{chat_id}/branch")
async def branch_chat(request: Request, chat_id: str, body: BranchChatRequest):
    """
    Create a new chat branching from an existing chat.
    Copies all messages and attachments up to and including the specified message.
    This allows exploring different conversation paths without losing the original.
    """
    database = request.app.state.database
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    # Verify source chat exists
    source_chat = database.get_chat(chat_id)
    if not source_chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")

    # Create branched chat in database
    branched_chat = database.branch_chat(
        source_chat_id=chat_id,
        up_to_message_id=body.message_id,
        new_title=body.title
    )

    if not branched_chat:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to branch chat. Message '{body.message_id}' may not exist in chat '{chat_id}'."
        )

    # Create chat service for the new branched chat
    try:
        # Get config from the branched chat
        config = ChatConfig(
            model=branched_chat.model,
            system_prompt=branched_chat.system_prompt,
            tool_servers=json.loads(branched_chat.tool_servers) if branched_chat.tool_servers else None,
            model_params=json.loads(branched_chat.model_params) if branched_chat.model_params else None,
        )
        
        chat_service_manager.create_service(
            chat_id=branched_chat.id,
            config=config
        )
    except Exception as e:
        # If chat service creation fails, clean up the branched chat
        database.delete_chat(branched_chat.id)
        raise HTTPException(status_code=500, detail=f"Failed to create chat service for branch: {str(e)}")

    # Get messages for the response
    messages = database.get_chat_history(branched_chat.id, limit=1000)

    return {
        "id": branched_chat.id,
        "title": branched_chat.title,
        "created_at": branched_chat.created_at.isoformat(),
        "updated_at": branched_chat.updated_at.isoformat(),
        "model": branched_chat.model,
        "system_prompt": branched_chat.system_prompt,
        "tool_servers": json.loads(branched_chat.tool_servers) if branched_chat.tool_servers else None,
        "model_params": json.loads(branched_chat.model_params) if branched_chat.model_params else None,
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


@router.post("/chats/{chat_id}/messages")
async def send_message(request: Request, chat_id: str, body: SendMessageRequest):
    """
    Send a message and get AI response.

    Supports both streaming and non-streaming responses.
    For streaming, set stream=true in request body and use Server-Sent Events (SSE).
    """
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager

    try:
        chat_service = chat_service_manager.get_service(chat_id)
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
        chat_service = chat_service_manager.get_service(chat_id)
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


@router.delete("/chats/{chat_id}/files/{filename}")
async def remove_uploaded_file(request: Request, chat_id: str, filename: str):
    """
    Remove a specific uploaded file from the chat context (pending upload state).
    """
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager
    
    try:
        chat_service = chat_service_manager.get_service(chat_id)
        
        # Construct the file path (same as upload path)
        uploads_dir = f"{request.app.state.app_config.uploads_dir}/{chat_id}"
        file_path = f"{uploads_dir}/{filename}"
        
        # Remove from chat service context
        chat_service.remove_uploaded_file(file_path)
        
        return {
            "success": True,
            "message": f"File {filename} removed from context"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove file: {str(e)}"
        )


@router.post("/chats/{chat_id}/github/files")
async def add_github_files_to_chat(request: Request, chat_id: str, body: AddGitHubFilesRequest):
    """
    Fetch files from GitHub and add them to the chat context.
    Supports both individual files and directories (which are expanded recursively).
    Optionally exclude specific paths.
    """
    github_client = request.app.state.github_client
    
    if not github_client:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration is not configured. Please set GITHUB_TOKEN environment variable."
        )
    
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager
    
    try:
        # Get or create chat service
        chat_service = chat_service_manager.get_service(chat_id)
        
        # Add files from GitHub
        added_paths = await chat_service.add_files_from_github(
            body.repo, 
            body.paths,
            body.exclude_paths
        )
        
        return {
            "success": True,
            "files_added": added_paths,
            "count": len(added_paths)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add files from GitHub: {str(e)}"
        )


@router.delete("/chats/{chat_id}/github/files")
async def remove_github_files_from_chat(request: Request, chat_id: str):
    """
    Remove all GitHub files from the chat context (pending upload state).
    Uploaded files are not affected.
    """
    chat_service_manager: ChatServiceManager = request.app.state.chat_service_manager
    
    try:
        chat_service = chat_service_manager.get_service(chat_id)
        chat_service.remove_github_files()
        
        return {
            "success": True,
            "message": "GitHub files removed from context"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove GitHub files: {str(e)}"
        )