from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from drpathcare.pagination import StandardResultsSetPagination
from bookings.models import Booking, BookingItem, BookingActionTracker
from bookings.serializers import BookingSerializer, BookingItemSerializer, BookingActionTrackerSerializer
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from bookings.utils.calculations import get_booking_calculations
from payments.utils import create_payment_link
from payments.models import BookingPayment
from bookings.utils.s3_utils import upload_to_s3 
from bookings.utils.invoice import generate_invoice_pdf
from users.models import User
from django.db.models import Count, Q


def build_verification_notes(booking):
    lines = ["Following are booked items at the time of verification:\n"]

    for item in booking.items.select_related(
        "lab_test", "profile", "package", "patient"
    ):
        # resolve product name
        if item.lab_test:
            product_name = item.lab_test.name
        elif item.profile:
            product_name = item.profile.name
        elif item.package:
            product_name = item.package.name
        else:
            product_name = "Unknown Item"

        patient_name = (
            item.patient.first_name + " " + item.patient.last_name if item.patient else "Unknown Patient"
        )

        lines.append(f"- {product_name} — {patient_name}")

    lines.append("\n")
    lines.append(f"Final booking amount: ₹{booking.final_amount}")

    return "\n".join(lines)

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().select_related("user", "address", "coupon").prefetch_related("items")
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__first_name", "user__last_name", "user__mobile", "remarks","user__email"]
    ordering_fields = ["created_at", "final_amount", "status", "payment_status","user__email"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        user_param = self.request.query_params.get("user")

        if not self.request.user.role:
            qs = qs.filter(user=self.request.user)
        else:
            if user_param:
                qs = qs.filter(user_id=user_param)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.annotate(
                payment_count=Count("payments", distinct=True),
                document_count=Count("documents", distinct=True),
            ).order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        data = self.request.data
        items_data = data.get("items", [])
        if not items_data:
            raise ValidationError("At least one booking item is required.")

        coupon_id = data.get("coupon")

        # ✅ 1. Validate calculations
        ok, result = get_booking_calculations(data, items_data, coupon_id)
        if not ok:
            raise ValidationError({"calculation_error": result})

        # ✅ 2. Create booking
        booking = serializer.save()

        # 2️⃣ Assign users AFTER creation
        if self.request.user.role is None:
            system_user = User.objects.get(id=40)
            booking.assigned_users.add(system_user)
        else:
            booking.assigned_users.add(self.request.user)


        # ✅ 3. Create booking items from validated result
        for item in result["items"]:
            BookingItem.objects.create(
                booking=booking,
                patient_id=item.get("patient"),
                lab_test_id=item["product_id"] if item["product_type"] == "lab_test" else None,
                profile_id=item["product_id"] if item["product_type"] == "lab_profile" else None,
                package_id=item["product_id"] if item["product_type"] == "lab_package" else None,
                base_price=item["base_price"],
                offer_price=item["offer_price"],
            )

        # ✅ 4. Save validated totals
        booking.base_total = result["base_total"]
        booking.offer_total = result["offer_total"]
        booking.coupon_discount = result["coupon_discount"]
        booking.admin_discount = result["admin_discount"]
        booking.discount_amount = result["total_discount"]
        booking.final_amount = result["final_amount"]
        booking.initial_amount = result["final_amount"]
        booking.total_savings = result["base_total"] - result["final_amount"]
        booking.save()

        # ✅ 5. Log creation
        BookingActionTracker.objects.create(
            booking=booking,
            user=self.request.user,
            action="create",
            notes="Booking created with validated totals and coupon",
        )

        return booking  # ← Booking is still returned here



    @transaction.atomic
    def perform_update(self, serializer):
        booking = serializer.instance
        data = self.request.data
        action_type = data.get("action_type")
        remarks = data.get("remarks", "").strip()

        if not remarks:
            raise ValidationError({"remarks": "Remarks are required for updates."})

        old_status = booking.status
        old_payment_status = booking.payment_status
        old_agent = booking.assigned_users

        payment_method = data.get("payment_method")
        payment_status = data.get("payment_status")
        new_status = data.get("status")
        new_agent_id = data.get("assigned_users")

        # === 1️⃣ Update Status ===
        if action_type == "update_status":
            if not new_status:
                raise ValidationError({"status": "Status is required for this action."})
            booking.status = new_status

            if new_status == "sample_collected":
                try:
                    generate_invoice_pdf(booking.id)
                except:
                    pass
            
            # ✅ SPECIAL CASE: VERIFIED
            if new_status == "verified" and booking.initial_amount:
                booking.initial_amount = booking.final_amount

                # 📝 Create verification snapshot
                verification_notes = build_verification_notes(booking)

                BookingActionTracker.objects.create(
                    booking=booking,
                    user=None,  # explicitly no user
                    action="add_remark",
                    notes=verification_notes,
                )

                booking.save(update_fields=["status", "initial_amount"])
            booking.save(update_fields=["status"])

        elif action_type == "update_agent":
            if not new_agent_id:
                raise ValidationError({"assigned_users": "Agent ID is required."})

            try:
                agents = User.objects.filter(id__in=new_agent_id)
            except User.DoesNotExist:
                raise ValidationError({"assigned_users": "Invalid agent ID"})

            # Existing assigned users
            assigned_users = booking.assigned_users.select_related("role").all()


            # Replace existing assigned users with this agent
            for user in agents:
                role_id = user.role.id 
                to_remove = booking.assigned_users.filter(role_id=role_id)
                if to_remove.exists():
                    booking.assigned_users.remove(*to_remove)
                booking.assigned_users.add(user.id)
                
                if user.role.name in ['Phlebo','Root Manager','Health Manager','Dietitian']:
                    print(user.role.name.lower().replace(" ","_"))
                    booking.status = user.role.name.lower().replace(" ","_")
                    booking.save(update_fields=["status"])
                

        # === 3️⃣ Payment Update ===
        elif action_type == "update_payment":
            if not payment_method:
                raise ValidationError({"payment_method": "Payment method is required."})

            booking.payment_method = payment_method
            report_uploaders = User.objects.filter(role__name='Report Uploader')
            if report_uploaders:
                for i in report_uploaders:
                    booking.assigned_users.add(i)
            else:
                booking.assigned_users.add(User.objects.get(id=5))

            if payment_method == "cash" or payment_method == "upi" :
                booking.payment_status = "success"
                booking.status = "payment_collected"
                booking.save(update_fields=["payment_method", "payment_status", "status"])

                # 🧾 Upload optional proof file via S3 utility
                file_obj = self.request.FILES.get("file")
                file_url = upload_to_s3(file_obj, prefix="cash_payments/") if file_obj else None

                # 💰 Create payment record
                BookingPayment.objects.create(
                    booking=booking,
                    amount=booking.final_amount,
                    method=payment_method,
                    status="success",
                    remarks=remarks,
                    file_url=file_url,  # proof of payment (optional)
                )

            elif payment_method == "online":
                booking.payment_status = payment_status or "initiated"
                booking.save(update_fields=["payment_method", "payment_status"])

                create_payment_link(
                    booking=booking,
                    amount=booking.final_amount,
                    email=booking.user.email,
                    phone=booking.user.mobile,
                )
        # === 4️⃣ Update Schedule (NEW) ===
        elif action_type == "update_schedule":
            new_date = data.get("scheduled_date")
            new_time = data.get("scheduled_time_slot")
            if not new_date or not new_time:
                raise ValidationError({"schedule": "Both date and time are required."})

            booking.scheduled_date = new_date
            booking.scheduled_time_slot = new_time
            booking.status = 'open'
            booking.save(update_fields=["scheduled_date", "scheduled_time_slot","status"])

        # === 5️⃣ Update Items (Revalidated with get_booking_calculations) ===
        elif action_type == "update_items":
            items_data = data.get("items", [])
            if not items_data:
                raise ValidationError({"items": "At least one booking item is required."})

            coupon_id = data.get("coupon")
            ok, result = get_booking_calculations(data, items_data, coupon_id)
            if not ok:
                raise ValidationError({"calculation_error": result})

            # 🧾 Drop old items
            booking.items.all().delete()

            # 🧮 Add new items from validated data
            for item in result["items"]:
                BookingItem.objects.create(
                    booking=booking,
                    patient_id=item.get("patient"),
                    lab_test_id=item["product_id"] if item["product_type"] == "lab_test" else None,
                    profile_id=item["product_id"] if item["product_type"] == "lab_profile" else None,
                    package_id=item["product_id"] if item["product_type"] == "lab_package" else None,
                    base_price=item["base_price"],
                    offer_price=item["offer_price"],
                )

            # ✅ Update booking totals from validated result
            booking.base_total = result["base_total"]
            booking.offer_total = result["offer_total"]
            booking.coupon_discount = result["coupon_discount"]
            booking.admin_discount = result["admin_discount"]
            booking.discount_amount = result["total_discount"]
            booking.final_amount = result["final_amount"]
            booking.total_savings = result["base_total"] - result["final_amount"]
            booking.coupon_id = data.get("coupon") or None
            booking.status = "open"
            booking.save(
                update_fields=[
                    "base_total",
                    "offer_total",
                    "coupon_discount",
                    "admin_discount",
                    "discount_amount",
                    "final_amount",
                    "total_savings",
                    "coupon",
                    "status",
                ]
            )

            # 💡 Optional: Incentive hook
            # for item in booking.items.all():
            #     if item.lab_test_id:
            #         create_incentive(item.lab_test_id, booking.id, self.request.user.id)

            action = "update_items"

        # === 6️⃣ Update Discounts (Coupon / Admin only) ===
        elif action_type == "update_discounts":
            coupon_id = data.get("coupon")
            admin_discount = float(data.get("admin_discount") or 0)

            # Fetch items for recalculation
            items_data = []
            for item in booking.items.all():
                items_data.append({
                    "patient": item.patient_id,
                    "base_price": item.base_price,
                    "offer_price": item.offer_price,
                    "lab_test": item.lab_test_id,
                    "profile": item.profile_id,
                    "package": item.package_id,
                })

            # Validate through shared helper
            ok, result = get_booking_calculations(data, items_data, coupon_id)
            if not ok:
                raise ValidationError({"calculation_error": result})

            # Update verified totals
            booking.coupon_id = coupon_id or None
            booking.admin_discount = result["admin_discount"]
            booking.coupon_discount = result["coupon_discount"]
            booking.discount_amount = result["total_discount"]
            booking.final_amount = result["final_amount"]
            booking.total_savings = result["base_total"] - result["final_amount"]
            booking.save(update_fields=[
                "coupon",
                "admin_discount",
                "coupon_discount",
                "discount_amount",
                "final_amount",
                "total_savings",
            ])

            action = "update_discounts"


        elif action_type == "add_remark":
            pass

        elif action_type == "upload_document":
            pass

        else:
            booking = serializer.save()

        # 🚫 Removed redundant booking.save()

        # --- Tracker logging ---
        action = action_type or "update"
        if booking.status != old_status:
            action = "status_change"
        elif booking.payment_status != old_payment_status:
            action = "payment_update"
        elif booking.assigned_users != old_agent:
            action = "agent_change"

        BookingActionTracker.objects.create(
            booking=booking,
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            notes=remarks or f"{action.replace('_', ' ').title()} performed.",
        )


class BookingItemViewSet(viewsets.ModelViewSet):
    queryset = BookingItem.objects.all().select_related("booking", "patient", "lab_test", "profile", "package")
    serializer_class = BookingItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["patient__first_name", "patient__last_name", "lab_test__name", "profile__name", "package__name"]
    ordering_fields = ["base_price", "offer_price", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        booking_id = self.request.query_params.get("booking")
        patient_id = self.request.query_params.get("patient")

        if not self.request.user.role:
            qs = qs.filter(booking__user=self.request.user)
        else:
            if booking_id:
                qs = qs.filter(booking_id=booking_id)
            if patient_id:
                qs = qs.filter(patient_id=patient_id)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        item = serializer.save()
        BookingActionTracker.objects.create(
            booking=item.booking,
            user=self.request.user if self.request.user.is_authenticated else None,
            action="add_item",
            notes=f"Item added: {item.id}",
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        booking = instance.booking
        instance.delete()
        BookingActionTracker.objects.create(
            booking=booking,
            user=self.request.user if self.request.user.is_authenticated else None,
            action="remove_item",
            notes="Item removed",
        )