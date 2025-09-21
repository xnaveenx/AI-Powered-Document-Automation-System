import os
import shutil
import boto3
from botocore.exceptions import ClientError

def ensure_folder(path: str):
    """Create folder if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def move_to_folder(src_file: str, dest_folder: str):
    """Move file to a local folder"""
    ensure_folder(dest_folder)
    dest_path = os.path.join(dest_folder, os.path.basename(src_file))
    shutil.move(src_file, dest_path)
    return dest_path

def upload_to_s3(src_file: str, bucket_name: str, key_prefix: str=""):
    """Upload file to s3 bucket"""
    s3_client=boto3.client("s3")
    file_name= os.path.basename(src_file)
    key= f"{key_prefix}/{file_name}" if key_prefix else file_name
    try:
        s3_client.upload_file(src_file, bucket_name, key)
        return f"s3://{bucket_name}/{key}"
    except ClientError as e:
        raise Exception(f"S3 upload failed: {str(e)}")
    
def send_to_erp_api(src_file: str, api_url: str, extra_data: dict = None):
    """Send file to ERP system via API"""
    import requests
    files={"file": open(src_file, "rb")}
    data = extra_data or {}
    response = requests.post(api_url, files=files, data=data)
    if response.status_code != 200:
        raise Exception(f"ERP API failed: {response.status_code} {response.text}")
    return response.text
    