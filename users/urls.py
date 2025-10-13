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
    LocationViewSet
)

# -----------------------------
# CRM Router (internal staff-facing APIs)
# -----------------------------
crm_router = DefaultRouter()
crm_router.register(r"users", UserViewSet, basename="crm-user")
crm_router.register(r"roles", RoleViewSet, basename="crm-role")
crm_router.register(r"patients", PatientViewSet, basename="crm-patient")
crm_router.register(r"addresses", AddressViewSet, basename="crm-address")


# -----------------------------
# Client Router (customer-facing APIs)
# -----------------------------
client_router = DefaultRouter()
client_router.register(r"patients", PatientViewSet, basename="client-patient")
client_router.register(r"addresses", AddressViewSet, basename="client-address")
client_router.register(r"location",LocationViewSet, basename="location")

# -----------------------------
# URL Patterns
# -----------------------------
urlpatterns = [
    # CRM endpoints
    path("crm/", include(crm_router.urls)),

    # Client endpoints
    path("client/", include(client_router.urls)),

    # Auth endpoints (common for both sides)
    path("auth/send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    
]
