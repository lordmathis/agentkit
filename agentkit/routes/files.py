import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agentkit.db.db import Database
from agentkit.routes.schemas import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(request: Request, file_id: str):
    """Get metadata for a file."""
    db: Database = request.app.state.database
    file_obj = db.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        id=file_obj.id, filename=file_obj.filename, content_type=file_obj.content_type
    )


@router.delete("/files/{file_id}")
async def delete_file(request: Request, file_id: str):
    """Delete a pending file."""
    import shutil

    db: Database = request.app.state.database
    file_obj = db.get_file(file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    if file_obj.status == "attached":
        raise HTTPException(status_code=400, detail="Cannot delete an attached file")

    # Delete from DB
    db.delete_file(file_id)

    # Delete from disk
    upload_dir = os.path.join("uploads", file_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    return {"status": "success"}
