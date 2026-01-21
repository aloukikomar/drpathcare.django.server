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

        valid_dfs = []
        skipped_sheets = []

        try:
            # -------------------------
            # CSV → single dataframe
            # -------------------------
            if file.name.lower().endswith(".csv"):
                df = pd.read_csv(file)
                valid_dfs.append(df)

            # -------------------------
            # EXCEL → read ALL sheets
            # -------------------------
            else:
                xls = pd.ExcelFile(file)

                for sheet_name in xls.sheet_names:
                    sheet_df = pd.read_excel(xls, sheet_name=sheet_name)

                    # normalize headers
                    sheet_df.columns = [
                        str(c).strip().lower() for c in sheet_df.columns
                    ]

                    received = set(sheet_df.columns)
                    missing = OLD_DATA_REQUIRED_COLUMNS.keys() - received

                    if missing:
                        skipped_sheets.append({
                            "sheet": sheet_name,
                            "missing_columns": sorted(missing),
                        })
                        continue

                    valid_dfs.append(sheet_df)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # -------------------------
        # NO VALID SHEETS
        # -------------------------
        if not valid_dfs:
            return Response(
                {
                    "error": "No valid sheets found",
                    "skipped_sheets": skipped_sheets,
                },
                status=400,
            )

        # -------------------------
        # MERGE ALL VALID SHEETS
        # -------------------------
        df = pd.concat(valid_dfs, ignore_index=True)

        created = skipped = 0
        new_objects = []

        from collections import defaultdict
        mobile_counts = defaultdict(int)

        # -------------------------
        # PROCESS ROWS
        # -------------------------
        for idx, row in df.iterrows():
            raw_mobile = row.get("mob no", "")
            raw_mobile = "" if pd.isna(raw_mobile) else str(raw_mobile)

            mobile = "".join(filter(str.isdigit, raw_mobile))

            if not mobile:
                print(
                    f"SKIPPED → row={idx+1} | invalid mobile='{raw_mobile}' | name='{row.get('name')}'"
                )
                skipped += 1
                continue

            mobile_counts[mobile] += 1

            row_data = {
                col: "" if pd.isna(row.get(col)) else str(row.get(col)).strip()
                for col in OLD_DATA_ALLOWED_COLUMNS
                if col in df.columns
            }

            new_objects.append(
                OldData(
                    mobile=mobile,
                    data=row_data,
                    source=f"{file.name}",
                )
            )
            created += 1

        # -------------------------
        # BULK INSERT
        # -------------------------
        OldData.objects.bulk_create(new_objects, batch_size=500)

        # -------------------------
        # DUPLICATE REPORTING
        # -------------------------
        duplicates = {m: c for m, c in mobile_counts.items() if c > 1}
        if duplicates:
            print("🔁 DUPLICATE MOBILES (NOT BLOCKED):")
            for m, c in duplicates.items():
                print(f"{m} → {c} rows")

        return Response(
            {
                "created": created,
                "skipped_rows": skipped,
                "total_rows": len(df),
                "valid_sheets": len(valid_dfs),
                "skipped_sheets": skipped_sheets,
                "duplicate_mobiles": len(duplicates),
            },
            status=200,
        )
