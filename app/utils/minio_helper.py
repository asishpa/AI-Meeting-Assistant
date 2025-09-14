from minio import Minio
from pydantic import BaseModel

from app.schemas.meet import MinioUploadResponse
import os
from dotenv import load_dotenv
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)
def upload_to_minio(local_file_path: str, bucket_name: str, object_name: str) -> MinioUploadResponse:
    """
    Upload a file to a MinIO bucket.
    Returns a MinioUploadResponse with status and object_name.
    """

    try:
        # Ensure the bucket exists
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)

        # Upload the file
        minio_client.fput_object(bucket_name, object_name, local_file_path)
        return MinioUploadResponse(status="success", object_name=object_name)
    except Exception as e:
        # Log the error securely (consider using a logger)
        return MinioUploadResponse(status="error", object_name=object_name, detail=str(e))