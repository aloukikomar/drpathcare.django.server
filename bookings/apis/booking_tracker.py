# bookings/apis_crm.py
from rest_framework import viewsets, permissions, filters
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import BookingActionTracker
from bookings.serializers import BookingActionTrackerListSerializer


class BookingActionTrackerCRMViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Fast CRM listing for booking action logs.
    Supports:
    - Filtering by booking
    - Search by notes and booking ref_id
    - Ordering by created_at (default)
    """
    queryset = BookingActionTracker.objects.select_related("booking", "user")
    serializer_class = BookingActionTrackerListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "notes",
        "booking__ref_id",
        "user__first_name",
        "user__last_name",
        "user__mobile",
    ]
    ordering_fields = ["created_at", "action"]

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user.role:
            return BookingActionTracker.objects.none()

        booking_id = self.request.query_params.get("booking")
        user_id = self.request.query_params.get("user")

        if booking_id:
            qs = qs.filter(booking_id=booking_id)

        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs.order_by("-created_at")
