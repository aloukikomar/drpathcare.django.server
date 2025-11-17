from rest_framework import viewsets, permissions,status
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import Address,Location
from users.serializers import AddressSerializer,LocationSerializer
from drpathcare.pagination import StandardResultsSetPagination
import csv
from io import TextIOWrapper
from rest_framework import filters 

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__first_name","line1","user__mobile"]
    # ordering_fields = ["user__email", "user__mobile", "first_name","last_name","date_of_birth", "created_at"]


    def get_queryset(self):
        user = self.request.user
        customer_id = self.request.query_params.get("customer")
        qs = self.queryset

        # Detect whether the request came from CRM or CLIENT router
        is_crm_request = self.request.path.startswith("/api/crm/")

        # ------------------------------
        # CRM MODE — staff with full access
        # ------------------------------
        if is_crm_request:
            if customer_id:
                return qs.filter(user_id=customer_id)
            return qs

        # ------------------------------
        # CLIENT MODE — staff behaves like customer
        # ------------------------------
        return qs.filter(user=user)

    

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["pincode","city","state"]
    ordering_fields = ["pincode","city","state"]


    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        """
        Upload CSV with columns: pincode,district,statename
        """
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)
        created = 0
        skipped = 0

        for row in reader:
            pincode = row.get("pincode")
            city = row.get("district")
            state = row.get("statename")
            if not pincode or not city or not state:
                continue  # skip invalid row

            if Location.objects.filter(pincode=pincode).exists():
                skipped += 1
                continue  # skip duplicates

            Location.objects.create(
                pincode=pincode,
                city=city,
                state=state,
                country="India"  # default
            )
            created += 1

        return Response(
            {"created": created, "skipped_duplicates": skipped},
            status=status.HTTP_201_CREATED,
        )
