from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID

class MeetRequest(BaseModel):
    meet_url: str
    guest_name: str = "Bot Recorder"
class MeetingProcessResult(BaseModel):
    transcript_file: Optional[str]
    merged_file: Optional[str]
    summary_file: Optional[str]
    success: bool
    error: Optional[str] = None
class MeetingMetadataDetails(BaseModel):
     id: UUID
     title: str | None
     model_config = {
        "from_attributes": True 
    }
class S3UploadResponse(BaseModel):
    status: str
    object_name: str
    url: str | None = None
    detail: str | None = None