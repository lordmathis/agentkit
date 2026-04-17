from typing import Optional

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    source: Optional[str] = None
