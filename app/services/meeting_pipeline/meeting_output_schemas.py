from pydantic import BaseModel
from typing import Optional, List


class NoteItem(BaseModel):
    topic: str
    start_time: str
    end_time: str
    items: List[str]
class ActionItem(BaseModel):
    assignnee: Optional[str]
    items: List[str]
class MeetingSummary(BaseModel):
    overview: str
    notes: List[NoteItem]
    action_items: List[ActionItem]