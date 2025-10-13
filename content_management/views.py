from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ContentManager
from .serializers import ContentManagerSerializer
from drpathcare.pagination import StandardResultsSetPagination


class ContentManagerViewSet(viewsets.ModelViewSet):
    queryset = ContentManager.objects.all().order_by("-created_at")
    serializer_class = ContentManagerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        media_type = self.request.query_params.get("media_type")
        if media_type:
            qs = qs.filter(media_type=media_type)
        return qs