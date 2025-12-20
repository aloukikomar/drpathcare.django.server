# payments/views.py
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from .models import BookingPayment,AgentIncentive
from .serializers import BookingPaymentSerializer,AgentIncentiveSerializer,AgentIncentiveBatchCreateSerializer
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from payments.utils import refresh_booking_payment_status, refresh_latest_payment_for_booking

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.html import escape
from django.views import View
import time
from django.db.models import Sum
from django.utils.timezone import make_aware
from datetime import datetime

class ClientBookingPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookingPaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["transaction_id", "gateway_order_id", "booking__id"]
    ordering_fields = ["created_at", "amount", "status"]

    def get_queryset(self):
        user = self.request.user
        return BookingPayment.objects.filter(
            booking__user=user
        ).select_related("booking")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Object-level security
        if instance.booking.user != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        return super().retrieve(request, *args, **kwargs)



class BookingPaymentViewSet(viewsets.ModelViewSet):
    queryset = BookingPayment.objects.all().select_related("booking", "user")
    serializer_class = BookingPaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["transaction_id", "provider_order_id", "booking__id", "user__email"]
    ordering_fields = ["created_at", "amount", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        booking_id = self.request.query_params.get("booking")
        status_param = self.request.query_params.get("status")
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        booking_payment = serializer.save()

        # 🔄 Auto-update booking payment summary
        booking = booking_payment.booking
        if booking_payment.status == "success":
            booking.payment_status = "success"
            booking.payment_method = booking_payment.method
            booking.save(update_fields=["payment_status", "payment_method"])

        return payment

    @transaction.atomic
    def perform_update(self, serializer):
        booking_payment = serializer.save()
        # 🔄 Sync booking if payment status changes
        booking = booking_payment.booking
        if booking_payment.status == "success":
            booking.payment_status = "success"
            booking.status = "payment_collected"
            booking.payment_method = booking_payment.method
        elif booking_payment.status == "failed":
            booking.payment_status = "failed"
        booking.save(update_fields=["payment_status", "payment_method"])
        return booking_payment

    @action(detail=True, methods=["post"], url_path="refresh-status")
    @transaction.atomic
    def refresh_status(self, request, pk=None):
        """
        POST /api/payments/<payment_id>/refresh-status/
        Refreshes the latest payment status from Razorpay.
        """
        payment = get_object_or_404(BookingPayment, pk=pk)

        try:
            updated_payment = refresh_booking_payment_status(payment)
            return Response(BookingPaymentSerializer(updated_payment).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path=r"booking/(?P<booking_id>[^/.]+)/refresh-latest")
    @transaction.atomic
    def refresh_latest_for_booking(self, request, booking_id=None):
        """
        POST /api/payments/booking/<booking_id>/refresh-latest/
        Refreshes the latest payment for a given booking.
        """
        try:
            updated_payment = refresh_latest_payment_for_booking(booking_id)
            return Response(BookingPaymentSerializer(updated_payment).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentConfirmationView(View):
    template_name = "payments/payment_confirmation.html"

    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return HttpResponse("Invalid booking reference", status=404)

        # 🧾 Refresh payment status
        try:
            payment = refresh_latest_payment_for_booking(booking_id)
            status = payment.status
        except Exception as e:
            status = "failed"
            # print(f"Payment refresh failed: {e}")

        # ✅ Map status to message
        status_message = {
            "success": "✅ Payment Successful! Thank you for your payment.",
            "failed": "❌ Payment Failed! Please try again.",
            "initiated": "⏳ Payment is still processing, please wait...",
        }.get(status, f"ℹ️ Payment status: {escape(status)}")

        # Render temporary page (auto-redirects to home)
        context = {
            "booking_id": booking.ref_id if hasattr(booking, "ref_id") else booking.id,
            "status": status,
            "message": status_message,
            "redirect_url": "https://drpathcare.com/",
        }
        return render(request, self.template_name, context)

class AgentIncentiveViewSet(viewsets.ModelViewSet):
    # queryset = (
    #     AgentIncentive.objects
    #     .select_related("agent", "booking")
    #     .order_by("-created_at")
    # )
    serializer_class = AgentIncentiveSerializer
    permission_classes = [IsAuthenticated]

    # ----------------------------------
    # Search / filter / ordering
    # ----------------------------------
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "agent__first_name",
        "agent__last_name",
        "agent__mobile",
        "booking__ref_id",
        "remark",
    ]

    filterset_fields = ["agent", "booking"]

    ordering_fields = ["amount", "created_at"]
    ordering = ["-created_at"]

    # ----------------------------------
    # QUERYSET with ASSIGNED USERS CHECK
    # ----------------------------------
    def get_queryset(self):
        user = self.request.user

        # CRM-only access
        if not user.role:
            return AgentIncentive.objects.none()

        qs = (
            AgentIncentive.objects
            .select_related("agent", "booking")
            .order_by("-created_at")
        )

        assigned_ids = getattr(user, "get_assigned_users", None)

        # ----------------------------------
        # Assigned users filter (ANY match)
        # booking.assigned_users ∩ user.get_assigned_users
        # ----------------------------------
        if assigned_ids:
            qs = qs.filter(
                booking__assigned_users__in=assigned_ids
            ).distinct()

        # ----------------------------------
        # DATE RANGE FILTER
        # ----------------------------------
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            try:
                start = make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
                qs = qs.filter(created_at__gte=start)
            except ValueError:
                pass  # silently ignore bad date

        if date_to:
            try:
                # include full day till 23:59:59
                end = make_aware(
                    datetime.strptime(date_to, "%Y-%m-%d")
                    .replace(hour=23, minute=59, second=59)
                )
                qs = qs.filter(created_at__lte=end)
            except ValueError:
                pass
        

        return qs


    # ----------------------------------
    # Serializer switch (bulk vs single)
    # ----------------------------------
    def get_serializer_class(self):
        if self.action == "create" and "items" in self.request.data:
            return AgentIncentiveBatchCreateSerializer
        return AgentIncentiveSerializer

    # ----------------------------------
    # BULK CREATE — first submission only
    # ----------------------------------
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 👉 Single create (unlikely but allowed)
        if "items" not in request.data:
            return super().create(request, *args, **kwargs)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = serializer.validated_data["booking_obj"]

        # ❌ Prevent second bulk creation
        if AgentIncentive.objects.filter(booking=booking).exists():
            return Response(
                {"detail": "Incentives already exist for this booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        objs = serializer.save()

        return Response(
            AgentIncentiveSerializer(objs, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    # ----------------------------------
    # SAFE UPDATE (FormDrawer)
    # ----------------------------------
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_amount = float(request.data.get("amount", instance.amount))

        total_other = (
            AgentIncentive.objects
            .filter(booking=instance.booking)
            .exclude(id=instance.id)
            .aggregate(total=Sum("amount"))["total"] or 0
        )

        if total_other + new_amount > instance.booking.final_amount:
            return Response(
                {"detail": "Total incentive exceeds booking final amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().partial_update(request, *args, **kwargs)
