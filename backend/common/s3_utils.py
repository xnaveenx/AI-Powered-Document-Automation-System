import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from backend.common.config import settings
import uuid

def upload_file(file_object, filename, content_type):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    try:
        unique_filename = f"{uuid.uuid4()}_{filename}"
        s3.upload_fileobj(
            file_object,
            settings.AWS_S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={'ContentType': content_type}
        )
        file_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
        return file_url
    except NoCredentialsError:
        raise Exception("AWS credentials not found.")
    except ClientError as e:
        raise Exception(f"Failed to upload file: {e}")