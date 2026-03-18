from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str
    filename: str
    content_type: str
