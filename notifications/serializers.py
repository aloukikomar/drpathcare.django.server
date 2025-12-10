from rest_framework import serializers
from .models import Notification
from .models import Enquiry
from users.models import User,Role

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
    # mobile = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = "__all__"

    # def get_mobile(self, obj):
    #     mobile = obj.mobile or ""
    #     if len(mobile) < 6:
    #         return mobile  # cannot mask properly

    #     # Mask mobile: 800xxxx271
    #     return f"{mobile[:3]}xxxx{mobile[-3:]}"


class EnquiryToUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, default="Male")
    age = serializers.IntegerField(required=False, allow_null=True)

    def create(self, validated_data):
        enquiry = self.context["enquiry"]

        # ✔ Email must ALWAYS exist → use blank string if missing
        email = validated_data.get("email") or ""

        # ✔ Mobile comes from enquiry (correct + safe)
        user = User.objects.create(
            mobile=enquiry.mobile,
            email=email,
            first_name=validated_data.get("first_name", enquiry.name.split()[0] if enquiry.name else ""),
            last_name=validated_data.get("last_name", ""),
            gender=validated_data.get("gender", "Male"),
            age=validated_data.get("age"),
        )

        # Link enquiry → user
        enquiry.user = user
        enquiry.save(update_fields=["user"])

        return user

    def update(self, instance, validated_data):
        # Not used for convert()
        pass
