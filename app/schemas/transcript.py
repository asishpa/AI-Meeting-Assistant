from pydantic import BaseModel

class TranscriptUtterance(BaseModel):
    start_time: str
    end_time: str
    text: str
    speaker: str
