from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from users.models import OTP
from users.serializers import SendOTPSerializer, VerifyOTPSerializer
import random
from rest_framework_simplejwt.tokens import RefreshToken
from notifications.utils import send_sms_from_template

from notifications.utils import send_otp_sms

User = get_user_model()

# -----------------------------
# Send OTP
# -----------------------------
CRM_ROLES = ["Admin", "Staff", "Manager","Agent"]  # update as per your role model
class SendOTPView(APIView):
    permission_classes = []

    def post(self, request):
        """
        Sends OTP for both registered and unregistered users.
        Returns:
            {
                "message": "OTP sent successfully",
                "is_user": true/false,
                "is_crm_user": true/false
            }
        """
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data["mobile"]

        # ✅ Generate OTP
        code = str(random.randint(1000, 9999))

        # ✅ Check if user exists
        user = User.objects.filter(mobile=mobile).first()
        is_user = bool(user)
        is_crm_user = bool(user and getattr(user, "role", None) and user.role.name in CRM_ROLES)

        # ✅ Save OTP (linked to user if exists, else None)
        otp = OTP.objects.create(
                    user=user if user else None,
                    mobile=user.mobile if user else mobile,
                    code=code
                )
        # ✅ Send SMS (works even if user=None)
        success, response_text, _ = send_otp_sms(mobile, code)

        if not success:
            return Response(
                {
                    "error": "Failed to send OTP",
                    "details": response_text,
                    "is_user": is_user,
                    "is_crm_user": is_crm_user,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": f"OTP sent to {mobile}",
                "is_user": is_user,
                "is_crm_user": is_crm_user,
            },
            status=status.HTTP_200_OK,
        )


# -----------------------------
# Verify OTP
# -----------------------------
class VerifyOTPView(APIView):
    permission_classes = []

    def post(self, request):
        from users.serializers import VerifyOTPSerializer  # import here to avoid circular import
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]
        otp_code = serializer.validated_data["otp"]

        user = User.objects.filter(mobile=mobile).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Check role
        if not user.role :
            return Response(
                {"error": "Access denied — not a CRM user"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ✅ Validate OTP
        otp_obj = (
            OTP.objects.filter(mobile=mobile, code=otp_code)
            .order_by("-created_at")
            .first()
        )

        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "OTP verified successfully",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "mobile": user.mobile,
                    "role": {
                                "id": user.role.id,
                                "name": user.role.name,
                                "view_all": user.role.view_all,
                                "permissions": user.role.permissions or [],
                            }
                },
            },
            status=status.HTTP_200_OK,
        )


class VerifyCustomerOTPView(APIView):
    """
    Verifies OTP for customers.
    - If user exists → login via OTP
    - If not → create user using provided data, then login
    """

    permission_classes = []

    def post(self, request):
        from users.serializers import VerifyOTPSerializer
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]
        otp_code = serializer.validated_data["otp"]

        # 🧩 Fetch latest OTP by mobile
        otp_obj = (
            OTP.objects.filter(mobile=mobile, code=otp_code)
            .order_by("-created_at")
            .first()
        )

        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # 🧩 Check if user exists
        user = User.objects.filter(mobile=mobile).first()
        print(request.data)
        # 🧩 If user doesn't exist, create from provided info
        if not user:
            user_data = {
                "mobile": mobile,
                "email": request.data.get("email"),
                "first_name": request.data.get("first_name"),
                "last_name": request.data.get("last_name"),
                "gender": request.data.get("gender", "Male"),
                "date_of_birth": request.data.get("date_of_birth"),
                "age": request.data.get("age"),
            }

            # # Default role for customer
            # customer_role = getattr(settings, "DEFAULT_CUSTOMER_ROLE_ID", None)
            # if customer_role:
            #     user_data["role_id"] = customer_role

            try:
                user = User.objects.create(**user_data)
            except Exception as e:
                return Response(
                    {"error": "Failed to create user", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            created = True
        else:
            created = False

        # 🧩 Issue JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "OTP verified successfully",
                "is_new_user": created,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "mobile": user.mobile,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.name if user.role else None,
                },
            },
            status=status.HTTP_200_OK,
        )
