from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated,AllowAny
from .models import Notification,Enquiry
from .serializers import NotificationSerializer,EnquirySerializer
from drpathcare.pagination import StandardResultsSetPagination

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        recipient_id = self.request.query_params.get("recipient")
        notification_type = self.request.query_params.get("notification_type")
        status = self.request.query_params.get("status")
        if recipient_id:
            qs = qs.filter(recipient_id=recipient_id)
        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        if status:
            qs = qs.filter(status=status)
        return qs


class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.all().order_by("-created_at")
    serializer_class = EnquirySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        # ✔ Only staff can see enquiries
        if not self.request.user.is_staff:
            return Enquiry.objects.none()

        return super().get_queryset()
