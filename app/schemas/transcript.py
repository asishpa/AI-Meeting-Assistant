from pydantic import BaseModel
from typing import Optional

class TranscriptUtterance(BaseModel):
    start_time: str
    end_time: str
    text: str
    speaker: Optional[str] = None
class TranscriptResponse(BaseModel):
    meeting_id: str
    transcript: list[TranscriptUtterance]
