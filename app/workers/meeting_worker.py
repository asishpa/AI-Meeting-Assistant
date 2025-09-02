import uuid
import docker  # pip install docker
from celery import Celery

celery_app = Celery(
    "meeting_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task
def record_meeting_task(request_data: dict):
    """
    Launch a dedicated Docker container for each meeting.
    """
    client = docker.from_env()

    # Unique output filenames
    meeting_id = str(uuid.uuid4())
    audio_file = f"meeting_{meeting_id}.wav"
    transcript_file = f"meeting_{meeting_id}.txt"

    # Run the container
    container = client.containers.run(
        "my-meeting-recorder:latest",   # Your image
        detach=True,
        remove=True,  # auto-cleanup
        environment={
            "MEET_URL": request_data["meet_url"],
            "GUEST_NAME": request_data.get("guest_name", "Meeting Bot"),
            "RECORD_SECONDS": str(request_data.get("record_seconds", 60)),
            "OUTPUT_FILE": audio_file,
            "TRANSCRIPT_FILE": transcript_file,
        },
        volumes={
            "/var/meetings": {  # host dir for storing results
                "bind": "/output",
                "mode": "rw",
            }
        },
        working_dir="/app"
    )

    # Wait until container finishes
    logs = container.logs(stream=True)
    for line in logs:
        print(line.decode().strip())

    exit_code = container.wait()["StatusCode"]

    if exit_code != 0:
        raise RuntimeError(f"Meeting bot failed with exit code {exit_code}")

    return {
        "audio_file": f"/var/meetings/{audio_file}",
        "transcript_file": f"/var/meetings/{transcript_file}"
    }
