from rest_framework.routers import DefaultRouter
from .views import ContentManagerViewSet

router = DefaultRouter()
router.register(r'content', ContentManagerViewSet, basename='content')

urlpatterns = router.urls