from pydantic import BaseModel
class MeetRequest(BaseModel):
    meet_url: str
    guest_name: str = "Bot Recorder"