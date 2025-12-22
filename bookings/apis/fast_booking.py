from rest_framework import viewsets, permissions, filters
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking
from bookings.serializers import BookingFastListSerializer
from django.conf import settings
from datetime import datetime
from django.db.models import Count, Q
from django.utils.timezone import make_aware

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

        # ----------------------------------
        # CRM-only access
        # ----------------------------------
        if not user.role:
            return Booking.objects.none()

        qs = Booking.objects.all()

        # ----------------------------------
        # Query params
        # ----------------------------------
        status_param = self.request.query_params.get("status")
        user_param = self.request.query_params.get("user")
        incentive = self.request.query_params.get("incentive")

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        assigned_ids = user.get_assigned_users

        # ----------------------------------
        # Standard filters
        # ----------------------------------
        if status_param:
            qs = qs.filter(status=status_param)

        if user_param:
            qs = qs.filter(user_id=user_param)

        # ----------------------------------
        # Assigned users filter (ANY match)
        # ----------------------------------
        if assigned_ids:
            qs = qs.filter(
                assigned_users__in=assigned_ids
            ).distinct()

        # ----------------------------------
        # Incentive filter
        # ----------------------------------
        if incentive is not None:
            incentive = incentive.lower()

            if incentive == "true":
                qs = qs.filter(incentives__isnull=True)

            elif incentive == "false":
                qs = qs.filter(incentives__isnull=False)

        
        # ----------------------------------
        # ✅ DATE RANGE FILTER
        # Applies to created_at OR scheduled_date
        # ----------------------------------
        if date_from and date_to:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()

            qs = qs.filter(
                Q(created_at__date__range=(df, dt)) |
                Q(scheduled_date__range=(df, dt))
            )
        # ----------------------------------
        # ⚡ SPEED OPTIMIZATION
        # ----------------------------------
        return (
            qs
            .distinct()  # REQUIRED because of M2M + joins
            .only(
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

