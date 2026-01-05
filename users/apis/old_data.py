# users/apis/bulk_contact.py

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import pandas as pd
from drpathcare.pagination import StandardResultsSetPagination

from users.models import OldData
from users.serializers import OldDataSerializer
from users.constants import (
    OLD_DATA_REQUIRED_COLUMNS,
    OLD_DATA_ALLOWED_COLUMNS,
)


class OldDataViewSet(viewsets.ModelViewSet):
    queryset = OldData.objects.all().order_by("-updated_at")
    serializer_class = OldDataSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter,filters.OrderingFilter]
    search_fields = ["mobile", "data__name"]
    ordering_fields = [
        "mobile",
        "created_at",
        "updated_at",

        # JSON fields
        "data__date",
        "data__name",
        "data__age",
        "data__gender",
        "data__no of member",
        "data__address",
        "data__land mark",
        "data__location",
        "data__pincode",
        "data__alt mob no",
        "data__email id",
        "data__whatsapp no",
        "data__package & test name",
        "data__package amount",
        "data__verify package amount",
        "data__team lead",
        "data__remark if any",
        "data__phlebo name",
        "data__lead type",
        "data__timing",
        "data__zone",
        "data__report done by",
        "data__status",
        "data__column1",
        "data__column2",
    ]

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    @transaction.atomic
    def bulk_upload(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "File is required"}, status=400)

        try:
            df = (
                pd.read_excel(file)
                if file.name.endswith("xlsx")
                else pd.read_csv(file)
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # -------------------------
        # NORMALIZE HEADERS
        # -------------------------
        df.columns = [str(c).strip().lower() for c in df.columns]

        received = set(df.columns)

        missing_required = OLD_DATA_REQUIRED_COLUMNS.keys() - received
        if missing_required:
            return Response(
                {
                    "error": "Missing required columns",
                    "missing": sorted(missing_required),
                    "received": sorted(received),
                },
                status=400,
            )

        # -------------------------
        # 🔥 DEDUPE FILE BY MOBILE
        # -------------------------
        deduped_rows = {}

        for _, row in df.iterrows():
            mobile = str(row.get("mob no", "")).strip()
            mobile = "".join(filter(str.isdigit, mobile))

            if not mobile:
                continue

            # last row wins
            deduped_rows[mobile] = row

        mobiles = list(deduped_rows.keys())

        # -------------------------
        # PREFETCH EXISTING (ONE DB HIT)
        # -------------------------
        existing = {
            obj.mobile: obj
            for obj in OldData.objects.filter(mobile__in=mobiles)
        }

        new_objects = []
        update_objects = []

        created = updated = skipped = 0

        # -------------------------
        # PROCESS DEDUPED ROWS
        # -------------------------
        for mobile, row in deduped_rows.items():
            row_data = {
                col: "" if pd.isna(row.get(col)) else str(row.get(col)).strip()
                for col in OLD_DATA_ALLOWED_COLUMNS
                if col in df.columns
            }

            if mobile in existing:
                obj = existing[mobile]
                obj.data.update(row_data)
                update_objects.append(obj)
                updated += 1
            else:
                new_objects.append(
                    OldData(
                        mobile=mobile,
                        data=row_data,
                        source=file.name,
                    )
                )
                created += 1

        if new_objects:
            OldData.objects.bulk_create(new_objects, batch_size=500)

        if update_objects:
            OldData.objects.bulk_update(
                update_objects,
                ["data", "updated_at"],
                batch_size=500,
            )

        return Response(
            {
                "created": created,
                "updated": updated,
                "deduped_rows": len(deduped_rows),
                "original_rows": len(df),
            },
            status=200,
        )
