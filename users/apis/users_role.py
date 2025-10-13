from rest_framework import viewsets, permissions
from users.models import Role,User
from users.serializers import UserSerializer, RoleSerializer
from drpathcare.pagination import StandardResultsSetPagination
from rest_framework import filters 

# -----------------------------
# Role CRUD
# -----------------------------
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination


# -----------------------------
# User CRUD
# -----------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "mobile", "first_name","last_name"]
    ordering_fields = ["email", "mobile", "first_name","last_name","date_of_birth", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        staff = self.request.query_params.get("staff")
        if staff:
            qs = qs.filter(is_staff=True)
        return qs