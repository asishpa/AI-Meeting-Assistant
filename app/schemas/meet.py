from pydantic import BaseModel, field_serializer
from typing import Dict, Optional, List, Any
from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

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
    meeting_date: datetime | None
    start_time: datetime | None

    model_config = {
        "from_attributes": True 
    }

    @field_serializer('start_time')
    def serialize_start_time(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        # Convert UTC to IST
        ist = ZoneInfo('Asia/Kolkata')
        if value.tzinfo is None:
            # If naive datetime, assume it's UTC
            value = value.replace(tzinfo=ZoneInfo('UTC'))
        ist_time = value.astimezone(ist)
        # Return only time in HH:MM:SS format
        return ist_time.strftime('%H:%M:%S')

class S3UploadResponse(BaseModel):
    status: str
    object_name: str
    url: str | None = None
    detail: str | None = None
class MeetingDetails(BaseModel):
    id: UUID
    title: str | None
    meeting_date: datetime | None
    participants: List[Any] | None
    transcript: List[Dict[str, Any]] | None = None
    summary: Dict[str, Any] | None
    start_time: datetime | None
    audio_url: str | None = None
    meet_url: str | None
    model_config = {
        "from_attributes": True 
    }

    @field_serializer('start_time')
    def serialize_start_time(self, value: datetime | None) -> str | None:
        if value is None or isinstance(value, str):
            return value
        # Convert UTC to IST
        ist = ZoneInfo('Asia/Kolkata')
        if value.tzinfo is None:
            # If naive datetime, assume it's UTC
            value = value.replace(tzinfo=ZoneInfo('UTC'))
        ist_time = value.astimezone(ist)
        # Return only time in HH:MM:SS format
        return ist_time.strftime('%H:%M:%S')