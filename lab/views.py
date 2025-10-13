# views.py
from rest_framework import viewsets, mixins,status
from rest_framework.permissions import IsAuthenticated
from .models import LabTest, Profile, Package,LabCategory
from .serializers import LabTestSerializer, ProfileSerializer, PackageSerializer, LabCategorySerializer
from drpathcare.pagination import StandardResultsSetPagination
import pandas as pd
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters 


class BaseLabViewSet(viewsets.GenericViewSet):
    """Common filtering logic shared by CRM & Client"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "test_code", "category__name"]
    ordering_fields = ["name", "test_code", "category__name", "price", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__name__icontains=category)
        return qs



# CRM = Full CRUD
class LabTestCRMViewSet(BaseLabViewSet, viewsets.ModelViewSet):
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        """
        Upload Excel file to create multiple LabTests at once
        Expected columns: name, test_code, investigation, sample_type,
        special_instruction, method, reported_on, category_name, price, sample_required
        """
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Excel file is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(file)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        errors = []

        for idx, row in df.iterrows():
            try:
                category_name = row.get("category_name")
                category = None
                if category_name:
                    category, _ = LabCategory.objects.get_or_create(name=category_name, entity_type="test")

                lab_test = LabTest.objects.create(
                            name=row.get("name"),
                            test_code=row.get("test_code"),
                            investigation=row.get("investigation"),
                            sample_type=row.get("sample_type"),
                            special_instruction=row.get("special_instruction"),
                            method=row.get("method"),
                            reported_on=row.get("reported_on"),
                            category=category,
                            price=row.get("price") or 0,
                            offer_price=row.get("offer_price") or None,
                            sample_required=row.get("sample_required")
                        )

                created.append(lab_test.id)
            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        return Response({"created": created, "errors": errors}, status=status.HTTP_201_CREATED)



class ProfileCRMViewSet(BaseLabViewSet, viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer


class PackageCRMViewSet(BaseLabViewSet, viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer


# Client = Read only
class LabTestClientViewSet(BaseLabViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer


class ProfileClientViewSet(BaseLabViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer


class PackageClientViewSet(BaseLabViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer


class LabCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LabCategory.objects.all().order_by("name")
    serializer_class = LabCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name","entity_type","description"]
    ordering_fields = ["name", "entity_type", "description", "created_at"]
    ordering = ["name"]  # default ordering

    pagination_class = StandardResultsSetPagination  # default

    def paginate_queryset(self, queryset):
        page_size = self.request.query_params.get("page_size")
        if page_size is None:
            return None  # disable pagination
        return super().paginate_queryset(queryset)


    def get_queryset(self):
        entity_type = self.request.query_params.get("entity_type")
        qs = super().get_queryset()
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return qs