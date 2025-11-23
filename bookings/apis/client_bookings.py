from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking, BookingActionTracker
from bookings.serializers import ClientBookingSerializer


class ClientBookingViewSet(viewsets.ModelViewSet):
    """
    Client-side Booking API:
    
    - GET    /api/client/bookings/       → list user's bookings
    - GET    /api/client/bookings/<id>/  → retrieve booking
    - PATCH  /api/client/bookings/<id>/  → reschedule OR cancel
    - POST disabled (checkout creates bookings)
    - PUT disabled
    """
    queryset = Booking.objects.all().select_related(
        "address", "coupon"
    ).prefetch_related("items", "payments", "documents")

    serializer_class = ClientBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = ["remarks", "ref_id", "address__line1", "address__pincode", "coupon__code"]
    ordering_fields = ["created_at", "final_amount", "status", "payment_status"]

    # ------------------------------
    # Queryset Control (Client vs CRM)
    # ------------------------------
    def get_queryset(self):
        qs = super().get_queryset()

        # CRM mode → full access
        is_crm = self.request.path.startswith("/api/crm/")
        if is_crm and self.request.user.is_staff:
            user_param = self.request.query_params.get("user")
            if user_param:
                qs = qs.filter(user_id=user_param)
            return qs.order_by("-created_at")

        # Client mode → only own bookings
        return qs.filter(user=self.request.user).order_by("-created_at")

    # ------------------------------
    # Disable Create
    # ------------------------------
    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Bookings can only be created via checkout API."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    # ------------------------------
    # PATCH Handler for Client Actions
    # ------------------------------
    def partial_update(self, request, *args, **kwargs):
        booking = self.get_object()
        user = request.user

        # Security check
        if booking.user != user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action")
        remarks = request.data.get("remarks", "").strip()

        if not action:
            return Response({"detail": "Action field is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --------------------------
        # 1️⃣ Reschedule
        # --------------------------
        if action == "reschedule":
            new_date = request.data.get("scheduled_date")
            new_slot = request.data.get("scheduled_time_slot")

            if not new_date or not new_slot:
                return Response(
                    {"detail": "scheduled_date and scheduled_time_slot are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            booking.scheduled_date = new_date
            booking.scheduled_time_slot = new_slot

            # Reset booking status
            booking.status = "open"
            booking.customer_status = "registered"

            booking.save(update_fields=[
                "scheduled_date", "scheduled_time_slot", "status", "customer_status"
            ])

            # Log tracker
            BookingActionTracker.objects.create(
                booking=booking,
                user=user,
                action="reschedule",
                notes=remarks or "Client rescheduled booking."
            )

            return Response({"detail": "Booking rescheduled successfully."},
                            status=status.HTTP_200_OK)

        # --------------------------
        # 2️⃣ Cancel
        # --------------------------
        if action == "cancel":
            booking.status = "cancelled"
            booking.customer_status = "cancelled"
            booking.save(update_fields=["status", "customer_status"])

            BookingActionTracker.objects.create(
                booking=booking,
                user=user,
                action="cancel",
                notes=remarks or "Client cancelled booking."
            )

            return Response({"detail": "Booking cancelled successfully."},
                            status=status.HTTP_200_OK)

        # --------------------------
        # ❌ Unsupported Actions
        # --------------------------
        return Response(
            {"detail": "Unsupported action for client."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ------------------------------
    # Prevent PUT
    # ------------------------------
    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Use PATCH for actions."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
