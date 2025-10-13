from rest_framework import viewsets, permissions
from users.models import Patient
from users.serializers import PatientSerializer
from drpathcare.pagination import StandardResultsSetPagination
from rest_framework import filters 

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name","last_name","user__mobile"]
    ordering_fields = ["user__email", "user__mobile", "first_name","last_name","date_of_birth", "created_at"]

    def get_queryset(self):
        # Users only see their own patients
        customer_id = self.request.query_params.get("customer")
        user = self.request.user
        qs = self.queryset
        if user.is_staff:
            if customer_id:
                qs = qs.filter(user_id=customer_id)
            return qs
        return qs.filter(user=user)
