from typing import List
from app.schemas.transcript import TranscriptUtterance, TranscriptResponse
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.schemas.meet import MeetRequest,MeetingMetadataDetails
from app.services.meetings.join_meeting import get_user_meetings
from app.workers.meeting_worker import record_meeting_task
from app.services.user_context import get_current_user
from app.schemas.transcript import TranscriptUtterance, TranscriptResponse
from app.services.meetings.transcript import get_merged_transcript
from sqlalchemy.orm import Session
from uuid import UUID


router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.post("/join-and-record")
async def join_and_record(request: MeetRequest, current_user=Depends(get_current_user)):

    payload = request.model_dump()
    job_data = {
        "request": payload,
        "user_id": current_user.user_id  # Server-provided user ID
    }
    job = record_meeting_task.delay(job_data)
    return {"status": "queued", "job_id": job.id}

# @router.get("/job-status/{job_id}")
# async def get_job_status(job_id: str):
#     job = record_meeting_task.AsyncResult(job_id)
#     if job.state == "PENDING":
#         return {"status": "pending"}
#     elif job.state == "SUCCESS":
#         return {"status": "completed", "result": job.result}
#     elif job.state == "FAILURE":
#         return {"status": "failed", "error": str(job.result)}
#     return {"status": job.state}
@router.get("/merged-transcript/{meeting_id}", response_model=TranscriptResponse)
async def merged_transcript(meeting_id: str, current_user=Depends(get_current_user), db_session=Depends(get_db)):
    utterances = await get_merged_transcript(meeting_id, current_user.user_id, db_session=db_session)
    return TranscriptResponse(meeting_id=meeting_id, transcript=utterances)



