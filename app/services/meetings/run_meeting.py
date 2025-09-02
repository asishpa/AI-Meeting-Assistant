import os
import logging
from app.schemas.meet import MeetRequest
from app.services.meetings.join_meeting import join_and_record_meeting
from app.utils.transcript import transcribe_file

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    meet_url = os.environ.get("MEET_URL")
    guest_name = os.environ.get("GUEST_NAME", "Meeting Bot")
    record_seconds = int(os.environ.get("RECORD_SECONDS", "60"))
    output_file = os.environ.get("OUTPUT_FILE", "meeting_audio.wav")
    transcript_file = os.environ.get("TRANSCRIPT_FILE", "meeting_transcript.txt")

    request = MeetRequest(meet_url=meet_url, guest_name=guest_name)

    logging.info(f"🚀 Starting meeting recording: {meet_url}")

    recorded_file = join_and_record_meeting(
        request,
        record_seconds=record_seconds,
        output_file=output_file
    )

    transcript = transcribe_file(recorded_file, transcript_file)

    logging.info(f"✅ Transcript generated at {transcript_file}")
