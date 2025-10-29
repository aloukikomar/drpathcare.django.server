import boto3
import uuid
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from .models import ContentManager
from .serializers import ContentManagerSerializer


class ContentManagerViewSet(viewsets.ModelViewSet):
    queryset = ContentManager.objects.all().order_by("-created_at")
    serializer_class = ContentManagerSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        file_obj = self.request.FILES.get("file")
        if not file_obj:
            raise ValueError("No file uploaded")

        # ✅ 1. Prepare S3 client
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        # ✅ 2. Generate unique filename
        ext = file_obj.name.split(".")[-1]
        filename = f"content/{uuid.uuid4()}.{ext}"

        # ✅ 3. Upload file to S3
        s3.upload_fileobj(
            file_obj,
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
            ExtraArgs={ "ContentType": file_obj.content_type},
        )

        # ✅ 4. Get public URL
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"

        # ✅ 5. Save record
        serializer.save(file_url=file_url)
