from rest_framework import serializers
from .models import Notification
from .models import Enquiry

class NotificationSerializer(serializers.ModelSerializer):
    recipient_mobile = serializers.CharField(source="recipient.mobile", read_only=True)
    recipient_email = serializers.CharField(source="recipient.email", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "recipient", "recipient_mobile","recipient_email", "notification_type",
            "subject", "message", "status", "error_message",
            "content_type", "object_id", "created_at", "updated_at"
        ]
        read_only_fields = ["status", "error_message", "created_at", "updated_at"]


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ["id", "name", "mobile", "enquiry", "created_at"]
