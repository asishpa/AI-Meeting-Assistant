from pydantic import BaseModel

class TranscriptUtterance(BaseModel):
    start_time: str
    end_time: str
    text: str
    speaker: str
class TranscriptResponse(BaseModel):
    meeting_id: str
    transcript: list[TranscriptUtterance]
