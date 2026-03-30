import logging
import mimetypes
import os
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Request, UploadFile

from agentkit.db.db import Database
from agentkit.routes.schemas import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/files", response_model=List[FileResponse])
async def upload_files(request: Request, files: List[UploadFile]):
    """Upload files via multipart form data."""
    db: Database = request.app.state.database
    result = []

    for upload in files:
        file_id = str(uuid.uuid4())
        upload_dir = os.path.join("uploads", file_id)
        os.makedirs(upload_dir, exist_ok=True)

        filename = upload.filename or file_id
        file_path = os.path.join(upload_dir, filename)

        content = await upload.read()
        with open(file_path, "wb") as f:
            f.write(content)

        content_type = (
            upload.content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        file_obj = db.create_file(
            filename=filename,
            file_path=os.path.abspath(file_path),
            content_type=content_type,
            file_id=file_id,
            source="upload",
        )

        result.append(
            FileResponse(
                id=file_obj.id,
                filename=file_obj.filename,
                content_type=file_obj.content_type,
                source=file_obj.source,
            )
        )

    return result


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
