# bookings/apis.py
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from bookings.models import BookingDocument
from bookings.serializers import BookingDocumentSerializer
from bookings.utils.s3_utils import upload_to_s3

class BookingDocumentViewSet(viewsets.ModelViewSet):
    queryset = BookingDocument.objects.all().order_by("-created_at")
    serializer_class = BookingDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        qs = super().get_queryset()
        booking_id = self.request.query_params.get("booking")
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
        return qs

    def perform_create(self, serializer):
        file_obj = self.request.FILES.get("file")
        if not file_obj:
            raise ValidationError({"file": "File is required."})

        file_url = upload_to_s3(file_obj, prefix="booking_docs/")
        serializer.save(file_url=file_url, uploaded_by=self.request.user)
