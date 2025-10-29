# payments/serializers.py
from rest_framework import serializers
from .models import BookingPayment
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer


class BookingPaymentSerializer(serializers.ModelSerializer):
    booking_detail = BookingSerializer(source="booking", read_only=True)
    user_detail = UserSerializer(source="user", read_only=True)

    class Meta:
        model = BookingPayment
        fields = [
            "id",
            "booking",
            "booking_detail",
            "user",
            "user_detail",
            "amount",
            "status",
            "method",
            "payment_link",          # ✅ renamed from "url"
            "gateway_response",      # ✅ new field for raw provider response
            "remarks",
            "metadata",
            "created_at",
            "updated_at",
            "file_url",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "payment_link",
            "gateway_response",
            "file_url",
        ]
