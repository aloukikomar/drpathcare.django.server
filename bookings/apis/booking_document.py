# bookings/apis.py
from rest_framework import viewsets,permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from bookings.models import BookingDocument
from bookings.serializers import BookingDocumentSerializer
from bookings.utils.s3_utils import upload_to_s3
from rest_framework.response import Response

class BookingDocumentViewSet(viewsets.ModelViewSet):
    queryset = BookingDocument.objects.all().order_by("-created_at")
    serializer_class = BookingDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        qs = super().get_queryset()
        booking_id = self.request.query_params.get("booking")
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
            # ⛔ Hide invoice if payment not successful
            qs = qs.exclude(
                    booking__payment_status__in=["pending", "initiated", "failed", "refunded", "not_required"],
                    doc_type="invoice"
                )

        return qs

    def perform_create(self, serializer):
        file_obj = self.request.FILES.get("file")
        if not file_obj:
            raise ValidationError({"file": "File is required."})

        file_url = upload_to_s3(file_obj, prefix="booking_docs/")
        serializer.save(file_url=file_url, uploaded_by=self.request.user)


class ClientBookingDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    CLIENT API:
    - GET /api/client/booking-documents/          → list user's documents
    - GET /api/client/booking-documents/<id>/     → retrieve single document
    """

    serializer_class = BookingDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        booking_id = self.request.query_params.get("booking")

        qs = BookingDocument.objects.filter(
            booking__user=user
        ).select_related("booking").order_by("-created_at")

        # ⛔ Hide invoice if payment not successful
        qs = qs.exclude(
                booking__payment_status__in=["pending", "initiated", "failed", "refunded", "not_required"],
                doc_type="invoice"
            )

        if booking_id:
            qs = qs.filter(booking_id=booking_id)

        return qs

    # Disable create/update/delete for client
    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Document upload is not allowed in client mode."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Update not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Delete not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
