from fastapi import APIRouter
from app.schemas.meet import MeetRequest
from app.workers.meeting_worker import record_meeting_task

router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.post("/join-and-record")
async def join_and_record(request: MeetRequest):
    job = record_meeting_task.delay(request.dict())
    return {"status": "queued", "job_id": job.id}

@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = record_meeting_task.AsyncResult(job_id)
    if job.state == "PENDING":
        return {"status": "pending"}
    elif job.state == "SUCCESS":
        return {"status": "completed", "result": job.result}
    elif job.state == "FAILURE":
        return {"status": "failed", "error": str(job.result)}
    return {"status": job.state}
