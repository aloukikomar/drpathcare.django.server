# payments/serializers.py
from rest_framework import serializers
from .models import BookingPayment,AgentIncentive,Booking
from bookings.serializers import BookingSerializer
from users.serializers import UserSerializer
from django.db import transaction


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
    agent_name = serializers.SerializerMethodField()
    booking_ref = serializers.CharField(source="booking.ref_id", read_only=True)
    booking_final_amount = serializers.CharField(source="booking.final_amount", read_only=True)

    class Meta:
        model = AgentIncentive
        fields = [
            "id",
            "agent",
            "agent_name",
            "booking",
            "booking_ref",
            "booking_final_amount",
            "amount",
            "remark",
            "created_at",
        ]

    def get_agent_name(self, obj):
        full = f"{obj.agent.first_name} {obj.agent.last_name}".strip()
        return full or obj.agent.first_name or obj.agent.last_name or ""


class AgentIncentiveBatchCreateSerializer(serializers.Serializer):
    booking = serializers.UUIDField()
    items = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate(self, data):
        booking_id = data["booking"]
        items = data["items"]

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"booking": "Invalid booking ID"})

        agent_ids = []
        total_amount = 0

        for idx, item in enumerate(items):
            agent_id = item.get("agent")
            amount = float(item.get("amount", 0))

            if not agent_id:
                raise serializers.ValidationError(
                    {f"items[{idx}].agent": "Agent is required"}
                )

            if amount < 0:
                raise serializers.ValidationError(
                    {f"items[{idx}].amount": "Amount cannot be negative"}
                )

            agent_ids.append(agent_id)
            total_amount += amount

        if len(agent_ids) != len(set(agent_ids)):
            raise serializers.ValidationError(
                "Duplicate agents are not allowed"
            )

        if total_amount > float(booking.final_amount):
            raise serializers.ValidationError(
                f"Total incentives ({total_amount}) "
                f"cannot exceed booking final amount ({booking.final_amount})"
            )

        data["booking_obj"] = booking
        return data

    @transaction.atomic
    def create(self, validated_data):
        booking = validated_data["booking_obj"]
        items = validated_data["items"]

        created = []
        for item in items:
            created.append(
                AgentIncentive.objects.create(
                    booking=booking,
                    agent_id=item["agent"],
                    amount=item.get("amount", 0),
                    remark=item.get("remark", ""),
                )
            )

        return created
