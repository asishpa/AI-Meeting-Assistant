from celery import Celery
import os
from app.services.meetings.join_meeting import join_and_record_meeting, process_meeting_transcript
from app.utils.transcript import transcribe_file_json
from app.schemas.meet import MeetRequest, MeetingProcessResult
import asyncio
from app.db.session import SessionLocal
from app.models.meeting import Meeting
from app.models.user import User
from app.utils.minio_helper import upload_to_minio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

minio_bucket = "meeting-audio"
celery_app = Celery(
    "meeting_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task
def record_meeting_task(request_data: dict):
    """
    Celery task to record meeting + generate transcript + capture captions.
    """
    async def run():
        request = MeetRequest(**request_data)

        audio_file = "meeting_audio.wav"
        #captions_file = "captions.json"
        #transcript_file = "meeting_transcript.json"
        #output_dir = "."  # where merged transcript + summary will be saved

        #  Join meeting, record audio + captions

        recorded_file, captions = join_and_record_meeting(
            request,
            record_seconds=300,
            output_file=audio_file
        )
        transcript = transcribe_file_json(recorded_file)

       
        
        minio_object = os.path.basename(recorded_file)
        minio_response = upload_to_minio(recorded_file, minio_bucket, minio_object)
        if minio_response.status == "success":
            logger.info(f"Successfully uploaded {minio_object} to MinIO bucket {minio_bucket}.")
        else:
            logger.error(f"Failed to upload {minio_object} to MinIO: {minio_response.detail}")
        # Optionally, handle minio_response (log, error handling, etc.)

        #  Process the meeting: transcribe, merge, generate summary
        results = process_meeting_transcript(
            transcript=transcript,
            captions=captions
        )

        # Prepare data for DB
        db_data = {
            "transcript": transcript,
            "summary": results.get("summary"),
            "captions": captions,
            "merged_transcript": results.get("merged_transcript") if "merged_transcript" in results else None,
            "user_id": request.user_id
        }
        save_meeting_to_db(request, db_data)
    return asyncio.run(run())
def save_meeting_to_db(request: MeetRequest, results: dict):
    
    db = SessionLocal()
    try:
        # Create meeting record
        meeting = Meeting(
            title="Meeting",
            #participants=participants,
            start_time=request.start_time,
            transcript=results.get("transcript"),
            summary=results.get("summary"),
            captions=results.get("captions"),
            merged_transcript=results.get("merged_transcript"),
            user_id=request.user_id
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    finally:
        db.close()
