from rest_framework import viewsets, permissions
from users.models import Role,User
from users.serializers import UserSerializer, RoleSerializer
from drpathcare.pagination import StandardResultsSetPagination
from rest_framework import filters 
from rest_framework import status
from rest_framework.response import Response

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
    search_fields = ["email", "mobile", "first_name", "last_name"]
    ordering_fields = [
        "email",
        "mobile",
        "first_name",
        "last_name",
        "date_of_birth",
        "created_at",
        "id",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("staff"):
            qs = qs.filter(role__isnull=False)
            # print(self.request.user.role,self.request.user.role == 'Report Uploader')
            if self.request.user and self.request.user.role.name != 'Admin':
                if self.request.user.role.name == 'Verifier':
                    qs = qs.filter(role__name='Root Manager')
                elif self.request.user.role.name == 'Report Uploader':
                    # print(self.request.user.role)
                    qs = qs.filter(role__name='Health Manager')
                    # print(qs)
                elif self.request.user.role.name == 'Health Manager':
                    # print(self.request.user.role)
                    qs = qs.filter(role__name='Dietitian')
                    # print(qs)
                else:    
                    
                    user_list = self.request.user.get_assigned_users if self.request.user.get_assigned_users else []
                    # print(user_list)
                    qs = qs.filter(id__in=user_list)
        return qs

    # ------------------------------------------------------
    # ⭐ FIX: allow email="" or null just like OTP creation
    # ------------------------------------------------------
    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # convert empty email "" → None
        if not data.get("email"):
            data["email"] = None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------
    # ⭐ FIX: update also must allow empty email=""
    # ------------------------------------------------------
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        data = request.data.copy()

        # convert empty "" → None
        if data.get("email") == "":
            data["email"] = None

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
