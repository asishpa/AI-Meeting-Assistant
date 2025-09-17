import os
import boto3
from pydantic import BaseModel
from app.schemas.meet import S3UploadResponse
import logging
from botocore.exceptions import ClientError
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- S3 setup ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
def upload_to_s3(file_path: str, bucket: str, object_name: str) -> S3UploadResponse:
    try:
        s3_client.upload_file(file_path, bucket, object_name)
        url = f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
        return S3UploadResponse(status="success", object_name=object_name, url=url)
    except Exception as e:
        return S3UploadResponse(status="error", object_name=object_name, detail=str(e))
def generate_presigned_url(bucket_name: str, object_name: str, expires_in: int = 3600) -> str:
    """
    Generate a temporary signed URL for an S3 object.
    """
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expires_in
        )
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None