from celery import Celery
from app.services.meetings.join_meeting import join_and_record_meeting, process_meeting_transcript
from app.utils.transcript import transcribe_file_json
from app.schemas.meet import MeetRequest
import asyncio

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
        captions_file = "captions.json"
        transcript_file = "meeting_transcript.json"
        output_dir = "."  # where merged transcript + summary will be saved

        # 1️⃣ Join meeting, record audio + captions
        recorded_file, captions_file = join_and_record_meeting(
            request,
            record_seconds=300,
            output_file=audio_file,
            captions_file=captions_file
        )
        transcript = transcribe_file_json(recorded_file, transcript_file)

        # 2️⃣ Process the meeting: transcribe, merge, generate summary
        results = process_meeting_transcript(
            audio_file=recorded_file,
            captions_file=captions_file,
            output_dir=output_dir
        )

        return results

    return asyncio.run(run())
