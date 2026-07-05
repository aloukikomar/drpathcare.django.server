from rest_framework import serializers
from .models import Patient, Address,Role,User,Location,OldData
from .utils import mask_mobile, should_mask_mobile_for
# from django.contrib.auth import get_user_model

# User = get_user_model()


class PatientSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_mobile = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_str = serializers.SerializerMethodField()

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name or ''} {obj.user.last_name or ''}".strip()
        return ""

    def _mobile(self, obj):
        if not obj.user:
            return ""
        mobile = obj.user.mobile or ""
        if should_mask_mobile_for(self.context.get("request"), obj.user):
            mobile = mask_mobile(mobile)
        return mobile

    def get_user_mobile(self, obj):
        return self._mobile(obj)

    def get_user_str(self, obj):
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            return f"{first} {last} | {self._mobile(obj)}".strip()
        return ""
    
    class Meta:
        model = Patient
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "pincode", "city", "state", "country"]


# -----------------------------
# Role Serializer
# -----------------------------
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class UserMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    mobile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name","mobile")

    def _mobile(self, obj):
        mobile = obj.mobile or ""
        if should_mask_mobile_for(self.context.get("request"), obj):
            mobile = mask_mobile(mobile)
        return mobile

    def get_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return self._mobile(obj)

    def get_mobile(self, obj):
        return self._mobile(obj)

# -----------------------------
# User Serializer
# -----------------------------
class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    # 👇 NEW FIELDS
    parent = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "mobile",
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "age",
            "user_code",        # ✅ ADD
            "role",
            "role_name",
            "mpin",
            "parent",           # ✅ ADD (id only, writeable)
            "parent_name",      # ✅ ADD (read-only display)
            "is_staff",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "role_name",
            "parent_name",
            "created_at",
            "updated_at",
        )

    # -----------------------------
    # Helpers
    # -----------------------------
    def get_parent_name(self, obj):
        if not obj.parent:
            return None
        return f"{obj.parent.first_name} {obj.parent.last_name}".strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if should_mask_mobile_for(self.context.get("request"), instance):
            data["mobile"] = mask_mobile(data["mobile"])
        return data


class SendOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


class AddressSerializer(serializers.ModelSerializer):
    pincode = serializers.CharField(source="location.pincode", read_only=True)
    city = serializers.CharField(source="location.city", read_only=True)
    state = serializers.CharField(source="location.state", read_only=True)
    user_mobile = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_str = serializers.SerializerMethodField()
    location = LocationSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    # Writable IDs
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source="location", write_only=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name or ''} {obj.user.last_name or ''}".strip()
        return ""

    def _mobile(self, obj):
        if not obj.user:
            return ""
        mobile = obj.user.mobile or ""
        if should_mask_mobile_for(self.context.get("request"), obj.user):
            mobile = mask_mobile(mobile)
        return mobile

    def get_user_mobile(self, obj):
        return self._mobile(obj)

    def get_user_str(self, obj):
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            return f"{first} {last} | {self._mobile(obj)}".strip()
        return ""

    class Meta:
        model = Address
        fields = "__all__"


class VerifyMPINSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    mpin = serializers.CharField(min_length=6, max_length=6)

    def validate_mpin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("MPIN must be numeric")
        return value


class OldDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = OldData
        fields = "__all__"