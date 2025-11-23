from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from users.models import User
from bookings.models import Booking, BookingDocument
from payments.models import BookingPayment

class ClientMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # GET /api/client/me/
    def get(self, request):
        user = request.user

        total_bookings = Booking.objects.filter(user=user).count()
        total_reports = BookingDocument.objects.filter(
            booking__user=user, doc_type="lab_report"
        ).count()
        total_payment = (
            BookingPayment.objects.filter(
                booking__user=user, status="success"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        return Response({
            "user": {
                "id": user.id,
                "email": user.email,
                "mobile": user.mobile,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "gender": user.gender,
                "date_of_birth": user.date_of_birth,
                "age": user.age,
            },
            "stats": {
                "total_bookings": total_bookings,
                "total_reports": total_reports,
                "total_payments": float(total_payment)
            }
        })

    # PATCH /api/client/me/
    def patch(self, request):
        user = request.user
        data = request.data

        # ❌ Block mobile modification
        if "mobile" in data and data["mobile"] != user.mobile:
            raise ValidationError({"mobile": "Mobile number cannot be changed."})

        # Email uniqueness check
        if "email" in data and data["email"] != user.email:
            if User.objects.filter(email=data["email"]).exists():
                raise ValidationError({"email": "Email already in use."})

        allowed_fields = [
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "age",
            "email",
        ]

        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        user.save()

        return Response({"detail": "Profile updated successfully."})
