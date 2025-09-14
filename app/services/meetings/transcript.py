from app.utils.transcript import TranscriptUtterance
from typing import List

def get_merged_transcript(meeting_id: str, user_id: str) -> List[TranscriptUtterance]:
    # TODO: Replace with actual DB fetch logic
    # For now, load from a static file as a placeholder
    transcript_path = f"meeting_transcript.txt"
    utterances = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                # Example format: start_time|end_time|speaker|text
                parts = line.strip().split("|")
                if len(parts) == 4:
                    utterances.append(TranscriptUtterance(
                        start_time=parts[0],
                        end_time=parts[1],
                        speaker=parts[2],
                        text=parts[3]
                    ))
    except Exception:
        pass
    return utterances
