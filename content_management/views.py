import boto3
import uuid
import json
from django.conf import settings
from rest_framework import viewsets, status,filters
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from .models import ContentManager
from .serializers import ContentManagerSerializer


class ContentManagerViewSet(viewsets.ModelViewSet):
    queryset = ContentManager.objects.all().order_by("-created_at")
    serializer_class = ContentManagerSerializer
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title", "description"]

    # ---------------------------------------
    #       GET  → Filter using tags
    # ---------------------------------------
    def get_queryset(self):
        qs = super().get_queryset()

        # 1️⃣ FULL JSON filter → tags={"type": "banner"}
        raw_tags = self.request.query_params.get("tags")
        if raw_tags:
            try:
                tag_dict = json.loads(raw_tags)
                for key, value in tag_dict.items():
                    qs = qs.filter(**{f"tags__{key}": value})
            except Exception:
                pass  # ignore invalid JSON

        # 2️⃣ Shorthand filter → tag_type=banner
        tag_type = self.request.query_params.get("tag_type")
        if tag_type:
            qs = qs.filter(tags__type=tag_type)

        return qs.order_by('tags__type')

    # ---------------------------------------
    #        CREATE  → Upload to S3
    # ---------------------------------------
    def perform_create(self, serializer):
        file_obj = self.request.FILES.get("file")
        if not file_obj:
            raise ValueError("No file uploaded")

        # 1. Init S3 client
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        # 2. Unique filename
        ext = file_obj.name.split(".")[-1]
        filename = f"content/{uuid.uuid4()}.{ext}"

        # 3. Upload
        s3.upload_fileobj(
            file_obj,
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": file_obj.content_type},
        )

        # 4. Public URL
        file_url = (
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3."
            f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"
        )

        # 5. Save
        serializer.save(file_url=file_url)



class PublicContentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContentManagerSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        qs = ContentManager.objects.all().order_by("-created_at")

        # Support tag-based filtering: ?tag_type=banner
        tags_params = {k: v for k, v in self.request.query_params.items() if k.startswith("tag_")}

        for key, value in tags_params.items():
            tag_key = key.replace("tag_", "")   # tag_type → type
            qs = qs.filter(**{f"tags__{tag_key}__iexact": value})

        return qs