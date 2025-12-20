# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AgentIncentiveViewSet,
    BookingPaymentViewSet,
    ClientBookingPaymentViewSet,
    PaymentConfirmationView,
)

# Admin / staff / internal router
router = DefaultRouter()
router.register("payments", BookingPaymentViewSet, basename="payment")
router.register("crm/incentives", AgentIncentiveViewSet, basename="incentives")


# Client-only router
client_router = DefaultRouter()
client_router.register("payments", ClientBookingPaymentViewSet, basename="client-payment")

urlpatterns = [
    # Admin/internal APIs
    path("", include(router.urls)),

    # Client-facing payment APIs
    path("client/", include(client_router.urls)),

    # Payment-confirmation endpoint
    path("payment-confirmation/<uuid:booking_id>/", 
         PaymentConfirmationView.as_view(), 
         name="payment-confirmation"),
]
