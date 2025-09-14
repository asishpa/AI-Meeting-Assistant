from fastapi import APIRouter, Depends
from app.services.user_context import get_current_user
from app.services.meetings.transcript import get_merged_transcript
from app.schemas.transcript import TranscriptUtterance

router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.get("/merged-transcript/{meeting_id}", response_model=list[TranscriptUtterance])
async def merged_transcript(meeting_id: str, current_user=Depends(get_current_user)):
    return await get_merged_transcript(meeting_id, current_user.id)
