from rest_framework.routers import DefaultRouter
from django.urls import path, include

from content_management.views import (
    ContentManagerViewSet,
    PublicContentViewSet
)

# CRM router (full CRUD)
crm_router = DefaultRouter()
crm_router.register(r'content', ContentManagerViewSet, basename='crm-content')

# Client router (GET only)
client_router = DefaultRouter()
client_router.register(r'content', PublicContentViewSet, basename='client-content')

urlpatterns = [
    path("crm/", include(crm_router.urls)),
    path("client/", include(client_router.urls)),
]
