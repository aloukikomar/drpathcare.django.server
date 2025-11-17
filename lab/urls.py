# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LabTestCRMViewSet, ProfileCRMViewSet, PackageCRMViewSet,
    LabTestClientViewSet, ProfileClientViewSet, PackageClientViewSet,LabCategoryViewSet,global_search,LabCategoryClientViewSet
)

crm_router = DefaultRouter()
crm_router.register(r'lab-category', LabCategoryViewSet, basename='crm-lab-category')
crm_router.register(r'lab-tests', LabTestCRMViewSet, basename='crm-labtest')
crm_router.register(r'lab-profiles', ProfileCRMViewSet, basename='crm-profile')
crm_router.register(r'lab-packages', PackageCRMViewSet, basename='crm-package')

client_router = DefaultRouter()
client_router.register(r'lab-category', LabCategoryClientViewSet, basename='client-lab-category')
client_router.register(r'lab-tests', LabTestClientViewSet, basename='client-labtest')
client_router.register(r'lab-profiles', ProfileClientViewSet, basename='client-profile')
client_router.register(r'lab-packages', PackageClientViewSet, basename='client-package')

urlpatterns = [
    path('crm/', include(crm_router.urls)),
    path('client/', include(client_router.urls)),
    path('client/search/', global_search, name='client-global-search'),
]