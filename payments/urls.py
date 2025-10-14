# payments/urls.py
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from .views import BookingPaymentViewSet, PaymentConfirmationView

router = DefaultRouter()
router.register("payments", BookingPaymentViewSet, basename="payment")


urlpatterns = [
    path("",include(router.urls)),
    path("payment-confirmation/<uuid:booking_id>/", PaymentConfirmationView.as_view(), name="payment-confirmation"),

]