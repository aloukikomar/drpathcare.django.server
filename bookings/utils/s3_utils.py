# utils/s3_utils.py
import boto3, uuid
from django.conf import settings

def upload_to_s3(file_obj, prefix="uploads/"):
    """
    Uploads a file object to AWS S3 and returns its public URL.
    """
    if not file_obj:
        raise ValueError("No file object provided for upload.")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    filename = f"{prefix}{uuid.uuid4()}_{file_obj.name}"
    s3.upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": file_obj.content_type},
    )

    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"
