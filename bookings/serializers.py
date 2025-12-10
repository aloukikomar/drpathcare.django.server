from rest_framework import serializers
from decimal import Decimal
from .models import (
    Cart, CartItem, Coupon, CouponRedemption, 
    Booking, BookingItem, BookingActionTracker,BookingDocument
)
from payments.models import BookingPayment
from users.serializers import (
    PatientSerializer, AddressSerializer, UserSerializer
)
from lab.serializers import LabTestSerializer, ProfileSerializer, PackageSerializer



class BookingFastListSerializer(serializers.ModelSerializer):
    user_str = serializers.SerializerMethodField()
    payment_count = serializers.IntegerField(read_only=True)
    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "ref_id",
            "user_str",
            "status",
            "payment_status",
            "final_amount",
            "created_at",
            "scheduled_date",
            "scheduled_time_slot",
            "payment_count",
            "document_count",
        ]

    def get_user_str(self, obj):
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        mobile = obj.user.mobile or ""

        # Mask mobile: 800xxxx271
        if len(mobile) >= 6:
            masked = mobile
            # masked = f"{mobile[:3]}xxxx{mobile[-3:]}"
        else:
            masked = mobile

        full_name = f"{first} {last}".strip()
        if not full_name:
            full_name = masked

        return f"{full_name} ({masked})"

# -------------------------
# Coupon Serializers
# -------------------------
class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "description", "discount_type", "discount_value",
            "max_discount_amount", "valid_from", "valid_to",
            "usage_limit", "per_user_limit", "active", "created_at"
        ]
        read_only_fields = ("created_at",)


class CouponRedemptionSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = CouponRedemption
        fields = ["id", "coupon", "coupon_code", "user", "user_email", "booking", "used_at"]
        read_only_fields = ("used_at",)



# -------------------------
# BookingItem Serializer
# -------------------------
class BookingItemSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)
    lab_test_detail = LabTestSerializer(source="lab_test", read_only=True)
    profile_detail = ProfileSerializer(source="profile", read_only=True)
    package_detail = PackageSerializer(source="package", read_only=True)

    class Meta:
        model = BookingItem
        fields = [
            "id", "booking", "patient", "patient_detail",
            "lab_test", "lab_test_detail",
            "profile", "profile_detail",
            "package", "package_detail",
            "base_price", "offer_price",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        # exactly one of lab_test, profile, package must be provided
        refs = [attrs.get("lab_test"), attrs.get("profile"), attrs.get("package")]
        if sum(1 for r in refs if r) != 1:
            raise serializers.ValidationError(
                "Provide exactly one of lab_test, profile, or package."
            )
        return attrs


# -------------------------
# BookingActionTracker Serializer
# -------------------------
class BookingActionTrackerSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = BookingActionTracker
        fields = ["id", "booking", "user", "user_email", "action", "notes", "created_at"]


class ClientPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingPayment
        fields = [
            "id", "amount", "status", "method",
            "payment_link", "gateway_payment_id",
            "gateway_order_id", "created_at"
        ]


class ClientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingDocument
        fields = [
            "id", "name", "file_url", "doc_type", "created_at"
        ]


class ClientBookingSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source="user", read_only=True)
    address_detail = AddressSerializer(source="address", read_only=True)

    items = BookingItemSerializer(many=True, read_only=True)

    # 🔥 FIX: removed redundant `source='payments'`
    payments = ClientPaymentSerializer(many=True, read_only=True)

    # 🔥 FIX: removed redundant `source='documents'`
    documents = ClientDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "ref_id",
            "status", "customer_status", "payment_status", "payment_method",
            "scheduled_date", "scheduled_time_slot",
            "remarks",
            
            # Totals
            "base_total", "offer_total", "total_savings",
            "final_amount", "discount_amount",

            # Relations
            "user_detail", "address_detail",

            # Nested
            "items", "payments", "documents",

            "created_at", "updated_at",
        ]
        read_only_fields = fields


# -------------------------
# Booking Serializer
# -------------------------
class BookingSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source="user", read_only=True)
    coupon_detail = CouponSerializer(source="coupon",read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    address_detail = AddressSerializer(source="address", read_only=True)

    items = BookingItemSerializer(many=True, read_only=True)
    create_items = BookingItemSerializer(many=True, write_only=True, required=False)

    actions = BookingActionTrackerSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Booking
        fields = [
            "id","ref_id", "user", "user_email", "current_agent", "address", "address_detail",
            "coupon", "coupon_code","coupon_detail", "discount_amount", "coupon_discount", "admin_discount",
            "base_total", "offer_total", "final_amount", "total_savings",
            "status","customer_status", "payment_status", "payment_method",
            "scheduled_date", "scheduled_time_slot", "remarks",
            "items", "create_items", "actions",
            "created_at", "updated_at", "user_detail",
        ]
        read_only_fields = [
            "id","ref_id", "base_total", "offer_total", "final_amount", "total_savings",
            "created_at", "updated_at",
        ]

    # -------------------------
    # Coupon helper
    # -------------------------
    def _apply_coupon(self, booking: Booking, coupon_code: str | None):
        if not coupon_code:
            return
        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({"coupon_code": "Invalid coupon code."})
        if not coupon.is_valid_now():
            raise serializers.ValidationError({"coupon_code": "Coupon is not active or valid now."})
        booking.coupon = coupon

    # -------------------------
    # Create Booking
    # -------------------------
    def create(self, validated_data):
        """
        ⚠️ Totals and item creation are handled in perform_create() using get_booking_calculations.
        The serializer only creates the bare booking record.
        """
        create_items = validated_data.pop("create_items", [])
        coupon_code = validated_data.pop("coupon_code", None)

        booking = Booking.objects.create(**validated_data)
        self._apply_coupon(booking, coupon_code)

        # Items & totals handled in the view
        return booking

    # -------------------------
    # Update Booking
    # -------------------------
    def update(self, instance: Booking, validated_data):
        """
        ⚠️ All calculation and item replacement logic is handled in perform_update().
        Serializer only updates fields and coupon.
        """
        coupon_code = validated_data.pop("coupon_code", None)
        create_items = validated_data.pop("create_items", [])

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if coupon_code is not None:
            self._apply_coupon(instance, coupon_code if coupon_code else None)

        instance.save()
        return instance




# -------------------------
# Cart & CartItem Serializers
# -------------------------
class CartItemSerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_type",
            "product_id",
            "product_name",
            "base_price",
            "offer_price",
            "effective_price",
            "created_at",
        ]

    def get_effective_price(self, obj):
        return obj.effective_price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_price", "total_items", "created_at"]
        read_only_fields = ["user", "created_at"]



class BookingDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    booking_code = serializers.SerializerMethodField()

    class Meta:
        model = BookingDocument
        fields = [
            "id",
            "booking",
            "booking_code",
            "name",
            "description",
            "file_url",
            "doc_type",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
         # ✅ file_url is now READ-ONLY
        read_only_fields = [
            "id",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "booking_code",
            "file_url",
        ]

    def get_uploaded_by_name(self, obj):
        user = getattr(obj, "uploaded_by", None)
        if not user:
            return None
        return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email or user.username

    def get_booking_code(self, obj):
        return getattr(obj.booking, "ref_id", None) or str(obj.booking_id)

    def validate(self, attrs):
        if not attrs.get("name"):
            raise serializers.ValidationError({"name": "Document name is required."})
        return attrs



class BookingActionTrackerListSerializer(serializers.ModelSerializer):
    booking_ref = serializers.CharField(source="booking.ref_id", read_only=True)
    user_str = serializers.SerializerMethodField()

    class Meta:
        model = BookingActionTracker
        fields = [
            "id",
            "booking",
            "booking_ref",
            "user_str",
            "action",
            "notes",
            "created_at",
        ]

    def get_user_str(self, obj):
        if not obj.user:
            return "system"
        mobile = obj.user.mobile or ""
        if len(mobile) >= 6:
            masked = mobile
            # masked = f"{mobile[:3]}xxxx{mobile[-3:]}"
        else:
            masked = mobile
        name = (obj.user.first_name or "") + " " + (obj.user.last_name or "")
        name = name.strip() or masked
        return f"{name} ({masked})"