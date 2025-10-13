# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from notifications.views import (
    NotificationViewSet
)

# -----------------------------
# CRM Router (internal staff-facing APIs)
# -----------------------------
crm_router = DefaultRouter()
crm_router.register(r"notifications", NotificationViewSet, basename="crm-notifications")

urlpatterns = [
    # CRM endpoints
    path("crm/", include(crm_router.urls)),

]
