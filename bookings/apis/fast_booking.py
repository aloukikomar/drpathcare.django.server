from rest_framework import viewsets, permissions, filters
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking
from bookings.serializers import BookingFastListSerializer
from django.db.models import Count

class BookingFastListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ultra-fast CRM listing endpoint.
    No nested data, minimal DB columns, optimized queries.
    """
    serializer_class = BookingFastListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "ref_id",
        "user__first_name",
        "user__last_name",
        "user__mobile",
    ]
    ordering_fields = ["created_at", "final_amount", "status"]

    def get_queryset(self):
        user = self.request.user

        # CRM-only
        if not user.is_staff:
            return Booking.objects.none()

        qs = Booking.objects.all()

        # Optional filters
        status_param = self.request.query_params.get("status")
        user_param = self.request.query_params.get("user")

        if status_param:
            qs = qs.filter(status=status_param)

        if user_param:
            qs = qs.filter(user_id=user_param)

        # ⚡ SPEED OPTIMIZATION
        return (
            qs.only(
                "id",
                "ref_id",
                "status",
                "payment_status",
                "final_amount",
                "created_at",
                "scheduled_date",
                "scheduled_time_slot",
                "user__first_name",
                "user__last_name",
                "user__mobile",
            )
            .select_related("user")
            .annotate(
                payment_count=Count("payments", distinct=True),
                document_count=Count("documents", distinct=True),
            )
            .order_by("-created_at")
        )
