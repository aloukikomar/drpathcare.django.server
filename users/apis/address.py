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
    ordering_fields = ["id","user__email", "user__mobile", "first_name","last_name","date_of_birth", "created_at"]


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
        Deduplicates by pincode before DB hit
        """
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decoded_file = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)

        # -----------------------------
        # STEP 1: Deduplicate CSV rows
        # -----------------------------
        csv_map = {}  # pincode -> {city, state}

        for row in reader:
            pincode = (row.get("pincode") or "").strip()
            city = (row.get("district") or "").strip()
            state = (row.get("statename") or "").strip()

            if not pincode or not city or not state:
                continue  # skip invalid rows

            # last occurrence wins (fine for master data)
            csv_map[pincode] = {
                "city": city,
                "state": state,
            }

        if not csv_map:
            return Response(
                {"created": 0, "skipped_duplicates": 0},
                status=status.HTTP_200_OK,
            )

        # ----------------------------------
        # STEP 2: Fetch existing pincodes
        # ----------------------------------
        existing_pincodes = set(
            Location.objects.filter(
                pincode__in=csv_map.keys()
            ).values_list("pincode", flat=True)
        )

        # ----------------------------------
        # STEP 3: Prepare bulk create list
        # ----------------------------------
        to_create = []
        skipped = 0

        for pincode, data in csv_map.items():
            if pincode in existing_pincodes:
                skipped += 1
                continue

            to_create.append(
                Location(
                    pincode=pincode,
                    city=data["city"],
                    state=data["state"],
                    country="India",
                )
            )

        # ----------------------------------
        # STEP 4: Bulk insert
        # ----------------------------------
        Location.objects.bulk_create(to_create, batch_size=1000)

        return Response(
            {
                "created": len(to_create),
                "skipped_duplicates": skipped,
                "total_rows_processed": len(csv_map),
            },
            status=status.HTTP_201_CREATED,
        )