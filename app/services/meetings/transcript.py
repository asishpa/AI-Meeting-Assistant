from app.utils.transcript import TranscriptUtterance
from typing import List
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.meeting import Meeting
from fastapi import HTTPException
from app.core.errors import TranscriptionError

async def get_merged_transcript(meeting_id: str, user_id: str, db_session=None) -> List[TranscriptUtterance]:
    if db_session is None:
        raise RuntimeError("DB session required")

    result = await db_session.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user_id)
    )
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found or access denied")

    merged = meeting.merged_transcript or {}
    transcript_items = merged.get("transcript", []) 

    utterances = []
    invalid_items = []
    for idx, item in enumerate(transcript_items):
        try:
            utterances.append(TranscriptUtterance(**item))
        except Exception as e:
            invalid_items.append({"index": idx, "item": item, "error": str(e)})

    if invalid_items:
        raise TranscriptionError(
            message=f"Invalid transcript items found: {invalid_items}"
        )

    return utterances
