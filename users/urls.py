# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from users.apis import (
    UserViewSet,
    RoleViewSet,
    PatientViewSet,
    AddressViewSet,
    SendOTPView,
    VerifyOTPView,
    LocationViewSet,
    VerifyCustomerOTPView,
    ClientMeAPIView
)

# -----------------------------
# CRM Router
# -----------------------------
crm_router = DefaultRouter()
crm_router.register(r"users", UserViewSet, basename="crm-user")
crm_router.register(r"roles", RoleViewSet, basename="crm-role")
crm_router.register(r"patients", PatientViewSet, basename="crm-patient")
crm_router.register(r"addresses", AddressViewSet, basename="crm-address")

# -----------------------------
# Client Router
# -----------------------------
client_router = DefaultRouter()
client_router.register(r"patients", PatientViewSet, basename="client-patient")
client_router.register(r"addresses", AddressViewSet, basename="client-address")
client_router.register(r"location", LocationViewSet, basename="location")

urlpatterns = [
    # CRM endpoints
    path("crm/", include(crm_router.urls)),

    # Client viewset endpoints
    path("client/", include(client_router.urls)),

    # Client me endpoint (APIView — cannot go in router)
    path("client/me/", ClientMeAPIView.as_view(), name="client-me"),

    # Auth endpoints
    path("auth/send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/verify-customer-otp/", VerifyCustomerOTPView.as_view(), name="verify-customer-otp"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
