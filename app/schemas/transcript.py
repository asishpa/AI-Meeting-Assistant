from pydantic import BaseModel

class TranscriptUtterance(BaseModel):
    id: str
    start_time: str
    end_time: str
    text: str
    duration_seconds: int
    speaker_name: str
    speaker_label: str
class TranscriptResponse(BaseModel):
    meeting_id: str
    transcript: list[TranscriptUtterance]
