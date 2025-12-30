# utils/s3_utils.py
import boto3
import uuid
from io import BytesIO
from django.conf import settings


def upload_to_s3(file_obj, prefix="uploads/"):
    """
    Uploads a file-like object or raw bytes to AWS S3
    and returns its public URL.

    Supports:
    - Django UploadedFile
    - BytesIO
    - raw bytes
    """

    if not file_obj:
        raise ValueError("No file object provided for upload.")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    # -------------------------
    # Normalize input
    # -------------------------
    content_type = "application/octet-stream"
    name = "file"

    # Case 1: raw bytes
    if isinstance(file_obj, (bytes, bytearray)):
        file_obj = BytesIO(file_obj)

    # Case 2: Django UploadedFile
    if hasattr(file_obj, "content_type"):
        content_type = file_obj.content_type or content_type

    if hasattr(file_obj, "name"):
        name = file_obj.name

    # Ensure file pointer is at start
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    if not hasattr(file_obj, "read"):
        raise ValueError("File object must implement read()")

    filename = f"{prefix}{uuid.uuid4()}_{name}"

    # -------------------------
    # Upload
    # -------------------------
    s3.upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": content_type},
    )

    return (
        f"https://{settings.AWS_STORAGE_BUCKET_NAME}"
        f".s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"
    )
