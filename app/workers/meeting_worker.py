from datetime import datetime, timezone
from celery import Celery
import os
from app.services.meetings.join_meeting import join_and_record_meeting, process_meeting_transcript
from app.utils.transcript import transcribe_file_json_aai,transcribe_file_json_deepgram
from app.schemas.meet import MeetRequest, MeetingProcessResult
import asyncio
from app.db.session import SessionLocal
from app.models.meeting import Meeting
from app.models.user import User
#from app.utils.minio_helper import upload_to_minio
from app.utils.s3 import upload_to_s3, S3_BUCKET
import logging
from app.services.meeting_pipeline.summarizer import generate_meeting_summary as generate_langchain_summary
from chatbot.indexing import index_meeting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

minio_bucket = "meeting-audio"
celery_app = Celery(
    "meeting_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task
def record_meeting_task(job_data: dict):
    """
    Celery task to record meeting + generate transcript + capture captions.
    """
    async def run():
        request_dict = job_data["request"]
        user_id = job_data["user_id"]
        request = MeetRequest(**request_dict)

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

        transcript = transcribe_file_json_deepgram(recorded_file)
        

        # Step 3: Upload audio to S3
        s3_object = os.path.basename(recorded_file)
        s3_response = upload_to_s3(recorded_file, S3_BUCKET, s3_object)

        audio_object = None
        audio_object = None
        if s3_response.status == "success":
            audio_object = s3_response.object_name
            logger.info(f"Uploaded to S3: {audio_object}")
        else:
            logger.error(f"S3 upload failed: {s3_response.detail}")

        # minio_object = os.path.basename(recorded_file)
        # minio_response = upload_to_minio(recorded_file, minio_bucket, minio_object)
        # if minio_response.status == "success":
        #     logger.info(f"Successfully uploaded {minio_object} to MinIO bucket {minio_bucket}.")
        # else:
        #     logger.error(f"Failed to upload {minio_object} to MinIO: {minio_response.detail}")
        # Optionally, handle minio_response (log, error handling, etc.)

        #  Process the meeting: transcribe, merge, generate summary
        results = process_meeting_transcript(
            transcript=transcript,
            captions=captions
        )
        speakers = list({seg["speaker_name"] for seg in results["merged_transcript"]["transcript"]})
        logger.info(f"Speakers detected: {speakers}")
        transcript_text = "\n".join(
        [f"{seg['speaker_name']}: {seg['text']}" for seg in results["merged_transcript"]["transcript"]]
)       
        logger.info(f"Transcript Text:\n{transcript_text}")
        index_meeting(meeting_id=request.meet_url, transcript_text=transcript_text)
        
        final_summary = generate_langchain_summary(transcript_text)
        logger.info(f"Final Summary:\n{final_summary}")
        # Prepare data for DB
        db_data = {
            "transcript": transcript,
            "summary": final_summary,
            "captions": captions,
            "merged_transcript": results.get("merged_transcript") if "merged_transcript" in results else None,
            "user_id": user_id,
            "meet_url": request.meet_url,  
            "audio_object": audio_object,
            "participants": speakers,   
        }
        save_meeting_to_db(request, db_data)
    return asyncio.run(run())

def save_meeting_to_db(request: MeetRequest, results: dict):
    
    db = SessionLocal()
    try:
        # Create meeting record
        meeting = Meeting(
            title="Meeting",
            participants=results.get("participants"),
            start_time=datetime.now(timezone.utc),
            transcript=results.get("transcript"),
            summary=results.get("summary"),
            captions=results.get("captions"),
            merged_transcript=results.get("merged_transcript"),
            user_id=results.get("user_id"),
            meet_url=request.meet_url,
            audio_url=results.get("audio_object")
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    finally:
        db.close()
