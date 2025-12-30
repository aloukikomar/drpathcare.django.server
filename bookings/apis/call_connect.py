# notifications/apis/call_connect.py

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from django.conf import settings

from users.models import User
from bookings.models import Booking
from notifications.models import Enquiry


class CallConnectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        call_type = request.data.get("call_type")

        if not call_type:
            raise ValidationError({"call_type": "This field is required"})

        from_number = request.user.mobile
        to_number = None

        # -------------------------
        # Resolve TO number
        # -------------------------
        if call_type == "booking":
            booking_id = request.data.get("booking_id")
            booking = Booking.objects.filter(id=booking_id).first()
            if not booking:
                raise ValidationError({"booking_id": "Invalid booking"})
            to_number = booking.user.mobile

        elif call_type == "enquiry":
            enquiry_id = request.data.get("enquiry_id")
            enquiry = Enquiry.objects.filter(id=enquiry_id).first()
            if not enquiry:
                raise ValidationError({"enquiry_id": "Invalid enquiry"})
            to_number = enquiry.mobile

        elif call_type == "customer":
            user_id = request.data.get("user_id")
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise ValidationError({"user_id": "Invalid user"})
            to_number = user.mobile

        elif call_type == "customer-booking":
            booking_id = request.data.get("booking_id")
            booking = Booking.objects.filter(id=booking_id).first()
            if not booking:
                raise ValidationError({"booking_id": "Invalid booking"})
            to_number = booking.user.mobile

        else:
            raise ValidationError({"call_type": "Invalid call_type"})

        if not from_number or not to_number:
            raise ValidationError("Mobile number missing")
        # -------------------------
        # Exotel API Call
        # -------------------------
        url = (
            f"https://{settings.EXOTEL_API_KEY}:{settings.EXOTEL_API_TOKEN}"
            f"@api.exotel.com/v1/Accounts/{settings.EXOTEL_ACCOUNT_SID}/Calls/connect"
        )

        payload = {
            "From": from_number,
            "To": to_number,
            "CallerId": settings.EXOTEL_CALLER_ID,
        }

        response = requests.post(url, data=payload, timeout=10)

        if response.status_code not in (200, 201):
            return Response(
                {
                    "success": False,
                    "message": "Call initiation failed",
                    "exotel_response": response.text,
                },
                status=400,
            )

        return Response(
            {
                "success": True,
                "call_type": call_type,
                "from": from_number,
                "to": to_number,
            }
        )
