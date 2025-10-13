# payments/views.py
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from .models import BookingPayment
from .serializers import BookingPaymentSerializer
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from payments.utils import refresh_booking_payment_status, refresh_latest_payment_for_booking



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