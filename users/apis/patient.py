from rest_framework import viewsets, permissions, filters
from users.models import Patient
from users.serializers import PatientSerializer
from drpathcare.pagination import StandardResultsSetPagination


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "user__mobile"]
    ordering_fields = ["user__email", "user__mobile", "first_name", "last_name", "date_of_birth", "created_at"]

    def get_queryset(self):
        user = self.request.user
        customer_id = self.request.query_params.get("customer")
        qs = self.queryset

        # ------------------------------
        # 🚩 Detect CRM vs Client route
        # ------------------------------
        is_crm_request = self.request.path.startswith("/api/crm/")

        # ------------------------------
        # ✅ CRM MODE — full access for staff
        # ------------------------------
        if is_crm_request:
            if customer_id:
                return qs.filter(user_id=customer_id)
            return qs

        # ------------------------------
        # ✅ CLIENT MODE — always restrict to own patients
        # staff should NOT get full access here
        # ------------------------------
        return qs.filter(user=user)
