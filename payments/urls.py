# payments/urls.py
from rest_framework.routers import DefaultRouter
from .views import BookingPaymentViewSet

router = DefaultRouter()
router.register("payments", BookingPaymentViewSet, basename="payment")

urlpatterns = router.urls
