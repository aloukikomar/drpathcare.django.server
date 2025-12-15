# payments/serializers.py
from rest_framework import serializers
from .models import BookingPayment,AgentIncentive
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer


class BookingPaymentSerializer(serializers.ModelSerializer):
    # booking_detail = BookingSerializer(source="booking", read_only=True)
    user_detail = UserSerializer(source="user", read_only=True)

    class Meta:
        model = BookingPayment
        fields = [
            "id",
            "booking",
            # "booking_detail",
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


class AgentIncentiveSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    booking_ref = serializers.CharField(source="booking.ref_id", read_only=True)

    class Meta:
        model = AgentIncentive
        fields = [
            "id",
            "user",
            "user_name",
            "booking",
            "booking_ref",
            "amount",
            "remark",
            "created_at",
        ]

    def get_user_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full or obj.user.first_name or obj.user.last_name or ""


class AgentIncentiveBatchCreateSerializer(serializers.Serializer):
    booking = serializers.UUIDField()
    incentives = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )

    def validate(self, data):
        booking_id = data["booking"]
        incentives = data["incentives"]

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Invalid booking ID")

        total_amount = sum(float(i.get("amount", 0)) for i in incentives)

        if total_amount > float(booking.final_amount):
            raise serializers.ValidationError(
                f"Total incentives ({total_amount}) cannot exceed booking final amount ({booking.final_amount})"
            )

        return data

    def create(self, validated_data):
        booking = Booking.objects.get(id=validated_data["booking"])
        incentives = validated_data["incentives"]

        created = []
        for item in incentives:
            obj = AgentIncentive.objects.create(
                booking=booking,
                user_id=item["user"],
                amount=item["amount"],
                remark=item.get("remark", "")
            )
            created.append(obj)

        return created
