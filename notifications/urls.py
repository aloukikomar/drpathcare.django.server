# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from notifications.views import (
    NotificationViewSet,EnquiryViewSet
)

# -----------------------------
# CRM Router (internal staff-facing APIs)
# -----------------------------
crm_router = DefaultRouter()
crm_router.register(r"notifications", NotificationViewSet, basename="crm-notifications")
crm_router.register(r"enquiries", EnquiryViewSet, basename="enquiry")

urlpatterns = [
    # CRM endpoints
    path("crm/", include(crm_router.urls)),

]
