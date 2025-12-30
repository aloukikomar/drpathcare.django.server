# bookings/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import BookingPublicDetailView
from bookings.apis import (
    BookingViewSet,
    BookingItemViewSet,
    BookingDocumentViewSet,
    BookingFastListViewSet,
    CartViewSet,
    CouponViewSet,
    CouponRedemptionViewSet,
    ClientBookingViewSet,
    ClientBookingDocumentViewSet,
    BookingActionTrackerCRMViewSet,
    DashboardAPIView,
    BookingBulkUpdateViewSet,
    CallConnectAPIView,
)

# -----------------------------------------------------
# 🔹 Router registration for all API endpoints
# -----------------------------------------------------
router = DefaultRouter()

# Booking-related routes
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'bookings-list', BookingFastListViewSet, basename='booking-list')
router.register(r'client/bookings', ClientBookingViewSet, basename='client-booking')
router.register(r'booking-items', BookingItemViewSet, basename='booking-item')
router.register(r'booking-documents', BookingDocumentViewSet, basename='booking-document')
router.register(r'client/booking-documents', ClientBookingDocumentViewSet, basename='client-booking-document')
router.register(
    r"booking-actions",
    BookingActionTrackerCRMViewSet,
    basename="crm-booking-actions"
)
router.register(
    r"bookings-bulk-update",
    BookingBulkUpdateViewSet,
    basename="booking-bulk-update",
)

# Cart & Coupon routes
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'coupons', CouponViewSet, basename='coupon')
router.register(r'coupon-redemptions', CouponRedemptionViewSet, basename='coupon-redemption')


# -----------------------------------------------------
# 🔹 URL patterns
# -----------------------------------------------------
urlpatterns = [
    path('', include(router.urls)),
    path("calls/connect/", CallConnectAPIView.as_view()),
    path(
        'crm/dashboard/',
        DashboardAPIView.as_view(),
        name='crm-dashboard'
    ),

    # Public booking details (no auth required)
    path(
        "booking-details/<uuid:booking_id>/",
        BookingPublicDetailView.as_view(),
        name="booking-public-view"
    ),
]
