from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from users.models import OTP
from users.serializers import SendOTPSerializer, VerifyOTPSerializer
import random
from rest_framework_simplejwt.tokens import RefreshToken
from notifications.utils import send_sms_from_template

User = get_user_model()

# -----------------------------
# Send OTP
# -----------------------------
class SendOTPView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data["mobile"]

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Generate OTP
        code = str(random.randint(1000, 9999))
        otp = OTP.objects.create(user=user, code=code)
        
        # -----------------------------
        # TODO: Send OTP via SMS/WhatsApp/email
        # send_otp(user.mobile, code)
        # -----------------------------
        send_sms_from_template(
                "OTP",
                user,
                {"otp": code},
            )
        
        return Response({"message": f"OTP sent to {mobile}"}, status=status.HTTP_200_OK)

# -----------------------------
# Verify OTP
# -----------------------------


class VerifyOTPView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data["mobile"]
        otp_code = serializer.validated_data["otp"]

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get latest OTP
        otp_obj = OTP.objects.filter(user=user, code=otp_code).order_by('-created_at').first()
        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is valid → issue JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "mobile": user.mobile,
                "role": user.role.name
            }
        }, status=status.HTTP_200_OK)