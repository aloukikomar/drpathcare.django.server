from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Sum, Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking
from payments.models import AgentIncentive
from notifications.models import Enquiry


# --------------------------------------------------
# DATE FILTER (BOOKINGS: created_at OR scheduled_date)
# --------------------------------------------------
def filter_booking_operational(qs, request):
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not (date_from and date_to):
        return qs

    df = datetime.strptime(date_from, "%Y-%m-%d").date()
    dt = datetime.strptime(date_to, "%Y-%m-%d").date()

    return qs.filter(
        Q(created_at__date__range=(df, dt)) |
        Q(scheduled_date__range=(df, dt))
    )


# --------------------------------------------------
# DATE FILTER (created_at ONLY)
# --------------------------------------------------
def filter_created_only(qs, request):
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not (date_from and date_to):
        return qs

    df = datetime.strptime(date_from, "%Y-%m-%d").date()
    dt = datetime.strptime(date_to, "%Y-%m-%d").date()

    return qs.filter(created_at__date__range=(df, dt))


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = user.role

        # --------------------------------------------------
        # BASE QUERYSETS (ONE TIME ONLY)
        # --------------------------------------------------
        bookings_qs = Booking.objects.all()
        enquiries_qs = Enquiry.objects.filter(is_active=True)
        incentives_qs = AgentIncentive.objects.all()

        # --------------------------------------------------
        # DATE FILTERS
        # --------------------------------------------------
        bookings_qs = filter_booking_operational(bookings_qs, request)
        enquiries_qs = filter_created_only(enquiries_qs, request)
        incentives_qs = filter_created_only(incentives_qs, request)

        # Revenue uses created_at ONLY
        revenue_qs = filter_created_only(Booking.objects.all(), request)

        # --------------------------------------------------
        # ROLE-BASED VISIBILITY
        # --------------------------------------------------
        if not role or not role.view_all:
            assigned_ids = user.get_assigned_users

            bookings_qs = bookings_qs.filter(
                assigned_users__in=assigned_ids
            ).distinct()

            revenue_qs = revenue_qs.filter(
                assigned_users__in=assigned_ids
            ).distinct()

            incentives_qs = incentives_qs.filter(agent=user)

        # --------------------------------------------------
        # METRICS
        # --------------------------------------------------
        total_bookings = bookings_qs.count()

        status_pie = list(
            bookings_qs
            .values("status")
            .annotate(count=Count("id"))
            .order_by()
        )

        data = {
            "total_bookings": total_bookings,
            "booking_status_pie": status_pie,
        }

        # --------------------------------------------------
        # ADMIN VIEW
        # --------------------------------------------------
        if role and role.view_all:
            completed_revenue = (
                revenue_qs
                .filter(status="completed")
                .aggregate(total=Sum("final_amount"))["total"]
                or Decimal("0.00")
            )

            potential_revenue = (
                revenue_qs
                .exclude(status="completed")
                .aggregate(total=Sum("final_amount"))["total"]
                or Decimal("0.00")
            )

            data.update({
                "revenue": {
                    "completed": completed_revenue,
                    "potential": potential_revenue,
                },
                "pending_enquiries": enquiries_qs.count(),
            })

        # --------------------------------------------------
        # AGENT VIEW
        # --------------------------------------------------
        else:
            total_incentive = (
                incentives_qs.aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            data["total_incentive"] = total_incentive

        return Response(data)
