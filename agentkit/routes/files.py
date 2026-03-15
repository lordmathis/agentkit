import logging
import os
import uuid
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from agentkit.db.db import Database

logger = logging.getLogger(__name__)

router = APIRouter()


class FileResponse(BaseModel):
    id: str
    filename: str
    content_type: str


class GitHubFilesRequest(BaseModel):
    repo: str
    paths: List[str]
    exclude_paths: List[str] = []


@router.post("/files", response_model=List[FileResponse])
async def upload_files(request: Request, files: List[UploadFile] = File(...)):
    """Upload one or more files and return their metadata."""
    db: Database = request.app.state.database
    result = []

    for upload_file in files:
        file_id = str(uuid.uuid4())
        # create directory: uploads/<file_id>/
        upload_dir = os.path.join("uploads", file_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, upload_file.filename)

        try:
            with open(file_path, "wb") as buffer:
                content = await upload_file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Failed to save file {upload_file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        content_type = upload_file.content_type or "application/octet-stream"

        # save to db with the generated file_id
        file_obj = db.create_file(
            filename=upload_file.filename,
            file_path=os.path.abspath(file_path),
            content_type=content_type,
            file_id=file_id,
        )

        result.append(
            FileResponse(
                id=file_obj.id,
                filename=file_obj.filename,
                content_type=file_obj.content_type,
            )
        )

    return result


@router.post("/files/github", response_model=List[FileResponse])
async def upload_github_files(request: Request, github_req: GitHubFilesRequest):
    """Fetch files from GitHub server-side, store to disk, and return their metadata."""
    db: Database = request.app.state.database
    from agentkit.routes.github import _expand_paths_to_files

    # Check if GitHub client is available
    github_client = getattr(request.app.state, "github_client", None)
    if not github_client:
        raise HTTPException(
            status_code=503, detail="GitHub integration is not configured."
        )

    # Expand paths
    try:
        file_paths = await _expand_paths_to_files(
            github_client, github_req.repo, github_req.paths, github_req.exclude_paths
        )
    except Exception as e:
        logger.error(f"Failed to expand GitHub paths: {e}")
        raise HTTPException(
            status_code=400, detail=f"Failed to expand GitHub paths: {e}"
        )

    db: Database = request.app.state.database
    result = []
    for path in file_paths:
        try:
            # Download file from GitHub
            content = await github_client.get_file_content(github_req.repo, path)
            filename = os.path.basename(path)

            # infer content_type
            import mimetypes

            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "text/plain"

            file_id = str(uuid.uuid4())
            upload_dir = os.path.join("uploads", file_id)
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, filename)

            # Save file
            with open(file_path, "wb") as f:
                if isinstance(content, str):
                    f.write(content.encode("utf-8"))
                else:
                    f.write(content)

            file_obj = db.create_file(
                filename=filename,
                file_path=os.path.abspath(file_path),
                content_type=content_type,
                file_id=file_id,
            )

            result.append(
                FileResponse(
                    id=file_obj.id,
                    filename=file_obj.filename,
                    content_type=file_obj.content_type,
                )
            )

        except Exception as e:
            logger.error(f"Failed to download and save GitHub file {path}: {e}")
            # we skip the file and continue or raise an exception? The requirements say "return same shape".
            # For robustness, we probably should raise or skip. Let's raise.
            raise HTTPException(
                status_code=500, detail=f"Failed to download GitHub file {path}: {e}"
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
