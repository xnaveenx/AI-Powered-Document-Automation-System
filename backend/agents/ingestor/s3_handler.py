import boto3
from backend.common.config import Settings
import logging

settings=Settings()
logger = logging.getLogger(__name__)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key= settings.AWS_SECRET_ACCESS_KEY
)

def upload_to_s3(file_path: str, s3_key: str) -> str:
    """
    Upload a file to s3 and return the s3 URL
    """
    try:
        s3_client.upload_file(file_path, settings.AWS_S3_BUCKET_NAME, s3_key)
        s3_url= f"https://{settings.AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        logger.info(f"Uploaded {file_path} to {s3_url}")
        return s3_url
    except Exception as e:
        logger.error(f"Failed to upload {file_path} to s3: {e}")
        raise