import os
import tempfile

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

router = APIRouter()


@router.post("/media/transcribe")
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
