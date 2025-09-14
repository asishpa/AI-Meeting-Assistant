from pydantic import BaseModel
from typing import Optional, List, Any
class MeetRequest(BaseModel):
    meet_url: str
    guest_name: str = "Bot Recorder"
class MinioUploadResponse(BaseModel):
        status: str
        object_name: str
class MeetingProcessResult(BaseModel):
    transcript_file: Optional[str]
    merged_file: Optional[str]
    summary_file: Optional[str]
    success: bool
    error: Optional[str] = None