# bookings/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import BookingPublicDetailView
from bookings.apis import BookingViewSet, BookingItemViewSet, CartViewSet, CouponViewSet, CouponRedemptionViewSet,BookingDocumentViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'booking-items', BookingItemViewSet, basename='booking-item')
router.register(r'booking-documents', BookingDocumentViewSet, basename='booking-document')


# new endpoints
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'coupons', CouponViewSet, basename='coupon')
router.register(r'coupon-redemptions', CouponRedemptionViewSet, basename='coupon-redemption')

urlpatterns = [
    path('', include(router.urls)),
    path("booking-details/<uuid:booking_id>/", BookingPublicDetailView.as_view(), name="booking-public-view"),
]
