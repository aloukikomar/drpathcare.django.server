from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Users app
    path('api/', include('users.urls')),  # includes users, roles, patients, addresses, OTP login
    path("api/", include("content_management.urls")), #s3 content
    path("api/", include("lab.urls")),
    path("api/", include("notifications.urls")),
    path('api/', include('bookings.urls')),
    path("api/", include("payments.urls")),
]