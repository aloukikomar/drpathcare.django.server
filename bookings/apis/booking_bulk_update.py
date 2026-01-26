# views/booking_bulk_update.py
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.exceptions import ValidationError

from bookings.models import Booking, BookingItem, BookingActionTracker
from bookings.serializers import BookingSerializer
from bookings.serializers import BookingBulkUpdateSerializer
from bookings.utils.calculations import get_booking_calculations



class BookingBulkUpdateViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingBulkUpdateSerializer
    queryset = Booking.objects.all()

    @transaction.atomic
    def partial_update(self, request, pk=None):
        booking = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        actions = data["actions"]
        remarks = data["remarks"]

        # -------------------------
        # UPDATE ITEMS
        # -------------------------
        if "update_items" in actions:
            items_data = data.get("items")
            if not items_data:
                raise ValidationError({"items": "Items are required"})

            coupon_id = data.get("coupon")

            ok, result = get_booking_calculations(
                request.data, items_data, coupon_id
            )
            if not ok:
                raise ValidationError({"calculation_error": result})

            booking.items.all().delete()

            for item in result["items"]:
                BookingItem.objects.create(
                    booking=booking,
                    patient_id=item.get("patient"),
                    lab_test_id=item["product_id"]
                    if item["product_type"] == "lab_test"
                    else None,
                    profile_id=item["product_id"]
                    if item["product_type"] == "lab_profile"
                    else None,
                    package_id=item["product_id"]
                    if item["product_type"] == "lab_package"
                    else None,
                    base_price=item["base_price"],
                    offer_price=item["offer_price"],
                )

            booking.base_total = result["base_total"]
            booking.offer_total = result["offer_total"]
            booking.coupon_discount = result["coupon_discount"]
            booking.admin_discount = result["admin_discount"]
            booking.discount_amount = result["total_discount"]
            booking.final_amount = result["final_amount"]
            booking.total_savings = (
                result["base_total"] - result["final_amount"]
            )
            booking.coupon_id = coupon_id or None
            booking.status = "open"

        # -------------------------
        # UPDATE DISCOUNTS
        # -------------------------
        if "update_discounts" in actions:
            coupon_id = data.get("coupon")
            admin_discount = float(data.get("admin_discount") or 0)

            items_data = []
            for item in booking.items.all():
                if item.lab_test_id:
                    product_type = "lab_test"
                    product_id = item.lab_test_id
                elif item.profile_id:
                    product_type = "lab_profile"
                    product_id = item.profile_id
                elif item.package_id:
                    product_type = "lab_package"
                    product_id = item.package_id
                else:
                    raise ValidationError("Invalid booking item")

                items_data.append({
                    "product_type": product_type,
                    "product_id": product_id,
                    "patient": item.patient_id,
                })

            ok, result = get_booking_calculations(
                request.data, items_data, coupon_id
            )
            if not ok:
                raise ValidationError({"calculation_error": result})

            booking.admin_discount = result["admin_discount"]
            booking.coupon_discount = result["coupon_discount"]
            booking.discount_amount = result["total_discount"]
            booking.final_amount = result["final_amount"]
            booking.total_savings = (
                result["base_total"] - result["final_amount"]
            )
            booking.coupon_id = coupon_id or None

        # -------------------------
        # UPDATE ADDRESS
        # -------------------------
        if "update_address" in actions:
            address_id = data.get("address")

            if not address_id:
                raise ValidationError({"address": "Address is required"})

            booking.address_id = address_id
            booking.status = "open"


        # -------------------------
        # UPDATE SCHEDULE
        # -------------------------
        if "update_schedule" in actions:
            date = data.get("scheduled_date")
            slot = data.get("scheduled_time_slot")

            if not date or not slot:
                raise ValidationError(
                    {"schedule": "Date & time required"}
                )

            booking.scheduled_date = date
            booking.scheduled_time_slot = slot
            booking.status = "rescheduled"

        booking.save()

        # -------------------------
        # TRACKING
        # -------------------------
        BookingActionTracker.objects.create(
            booking=booking,
            user=request.user,
            action="bulk_update",
            notes=remarks+ "\n- {}".format(",".join(actions)),
        )

        return Response(
            BookingSerializer(booking).data
        )
