from datetime import datetime, timezone
from celery import Celery
import os
import logging
import shutil

from app.services.meetings.join_meeting import join_and_record_meeting, process_meeting_transcript
from app.utils.transcript import transcribe_file_json_deepgram
from app.schemas.meet import MeetRequest
from app.db.session import SessionLocal  # <- sync session for Celery
from app.models.meeting import Meeting
from app.utils.s3 import upload_to_s3, S3_BUCKET
from app.services.meeting_pipeline.summarizer import generate_meeting_summary as generate_langchain_summary
from chatbot.indexing import index_meeting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_AUDIO_DIR = "/tmp/meetings"

celery_app = Celery(
    "meeting_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task
def record_meeting_task(job_data: dict):
    """
    Celery task to record meeting + generate transcript + capture captions.
    Fully sync-safe for DB operations.
    """
    run_meeting_task(job_data)


def run_meeting_task(job_data: dict):
    request_dict = job_data["request"]
    user_id = job_data["user_id"]
    request = MeetRequest(**request_dict)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    meeting_id = request.meet_url.replace("https://", "").replace("/", "_")
    meeting_folder = os.path.join(BASE_AUDIO_DIR, str(user_id), meeting_id, timestamp)
    os.makedirs(meeting_folder, exist_ok=True)

    audio_file = os.path.join(meeting_folder, "meeting_audio.wav")

    # Step 1 — Join meeting, record audio + captions
    recorded_file, captions = join_and_record_meeting(
        request,
        record_seconds=300,
        output_file=audio_file
    )

    # Step 2 — Transcribe audio
    transcript = transcribe_file_json_deepgram(recorded_file)

    # Step 3 — Upload audio to S3
    s3_key = f"meetings/{user_id}/{meeting_id}/{timestamp}/meeting_audio.wav"
    s3_response = upload_to_s3(recorded_file, S3_BUCKET, s3_key)

    audio_object = None
    if s3_response.status == "success":
        audio_object = s3_key
        logger.info(f"Uploaded to S3: {audio_object}")
    else:
        logger.error(f"S3 upload failed: {s3_response.detail}")

    # Step 4 — Process transcript and generate summary
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

    meeting_id = request.meet_url.rstrip("/").split("/")[-1]
    index_meeting(meeting_id=meeting_id, transcript_text=transcript_text)

    final_summary = generate_langchain_summary(transcript_text)
    logger.info(f"Final Summary:\n{final_summary}")

    # Step 5 — Save meeting to DB (sync)
    db_data = {
        "transcript": transcript,
        "summary": final_summary,
        "captions": captions,
        "merged_transcript": results.get("merged_transcript"),
        "user_id": user_id,
        "meet_url": request.meet_url,
        "audio_object": audio_object,
        "participants": speakers,
    }
    save_meeting_to_db(request, db_data)

    # Step 6 — Clean up
    shutil.rmtree(meeting_folder, ignore_errors=True)


def save_meeting_to_db(request: MeetRequest, results: dict):
    """
    Sync DB save for Celery worker
    """
    with SessionLocal() as db:
        meeting = Meeting(
            title="Meeting",
            participants=results.get("participants"),
            start_time=datetime.now(timezone.utc),
            transcript=[utt.dict() for utt in results.get("transcript", [])],
            summary=results.get("summary"),
            captions=results.get("captions"),
            merged_transcript=results.get("merged_transcript"),
            user_id=results.get("user_id"),
            meet_url=request.meet_url,
            audio_object=results.get("audio_object")
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    return meeting
