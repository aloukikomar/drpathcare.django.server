from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Notification, Enquiry
from .serializers import (
    NotificationSerializer,
    EnquirySerializer,
    EnquiryToUserSerializer,
)
from drpathcare.pagination import StandardResultsSetPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from users.models import User


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "recipient__first_name",
        "recipient__last_name",
        "recipient__mobile",
    ]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        recipient_id = self.request.query_params.get("recipient")
        notification_type = self.request.query_params.get("notification_type")
        status = self.request.query_params.get("status")

        if recipient_id:
            qs = qs.filter(recipient_id=recipient_id)
        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        if status:
            qs = qs.filter(status=status)

        return qs


class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.all().order_by("-created_at")
    serializer_class = EnquirySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        # ✔ Only staff can see enquiries
        if not self.request.user.is_staff:
            return Enquiry.objects.none()
        return super().get_queryset()

    # ----------------------------------------------
    # ⭐ NEW: Auto-link enquiry → existing user
    # ----------------------------------------------
    def create(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")

        # find user by mobile
        user = None
        if mobile:
            user = User.objects.filter(mobile=mobile).first()

        # pass user into serializer context
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save(user=user)

        return Response(
            EnquirySerializer(enquiry).data,
            status=status.HTTP_201_CREATED
        )

    # ----------------------------------------------
    # ⭐ NEW: Convert Enquiry → Customer (User)
    #    (Fully aligned with OTP method)
    # ----------------------------------------------
    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        enquiry = self.get_object()

        # same logic as VerifyCustomerOTPView
        email = request.data.get("email") or None
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        gender = request.data.get("gender") or "Male"
        age = request.data.get("age")
        dob = request.data.get("date_of_birth")

        # Prevent duplicate-user creation
        existing = User.objects.filter(mobile=enquiry.mobile).first()
        if existing:
            return Response(
                {"error": "A customer already exists for this mobile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.create(
                mobile=enquiry.mobile,
                email=email,  # NULL allowed, behaves same as OTP
                first_name=first_name or enquiry.name,
                last_name=last_name or "",
                gender=gender,
                date_of_birth=dob,
                age=age,
            )
        except Exception as e:
            return Response(
                {"error": "Failed to create customer", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Link enquiry to this new user
        enquiry.user = user
        enquiry.save(update_fields=["user"])

        return Response(
            {
                "message": "Customer created successfully",
                "user_id": user.id,
            },
            status=status.HTTP_201_CREATED,
        )
