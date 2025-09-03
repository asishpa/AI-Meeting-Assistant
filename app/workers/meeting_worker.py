from celery import Celery
from app.services.meetings.join_meeting import join_and_record_meeting
from app.utils.transcript import transcribe_file
import asyncio

celery_app = Celery(
    "meeting_worker",
    broker="redis://localhost:6379/0",   # redis service from docker-compose
    backend="redis://localhost:6379/0"
)

@celery_app.task
def record_meeting_task(request_data: dict):
    """
    Celery task to record meeting + generate transcript + capture captions.
    """
    async def run():
        from app.schemas.meet import MeetRequest
        request = MeetRequest(**request_data)

        audio_file = "meeting_audio.wav"
        captions_file = "captions.txt"
        transcript_file = "meeting_transcript.txt"

        recorded_file, captions_file = join_and_record_meeting(
            request,
            record_seconds=300,
            output_file=audio_file,
            captions_file=captions_file
        )

        # Generate transcript from recorded audio
        transcript = transcribe_file(recorded_file, transcript_file)

        return {
            "audio_file": recorded_file,
            "captions_file": captions_file,
            "transcript_file": transcript_file,
            "transcript": transcript
        }

    return asyncio.run(run())

