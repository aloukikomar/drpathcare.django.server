from rest_framework import serializers
from .models import Patient, Address,Role,User,Location
# from django.contrib.auth import get_user_model

# User = get_user_model()


class PatientSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_mobile = serializers.CharField(source="user.mobile", read_only=True)
    user_name = serializers.SerializerMethodField()
    user_str = serializers.SerializerMethodField()

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name or ''} {obj.user.last_name or ''}".strip()
        return ""

    def get_user_str(self, obj):
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            mobile = obj.user.mobile or ""
            return f"{first} {last} | {mobile}".strip()
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

    class Meta:
        model = User
        fields = ("id", "name","mobile")

    def get_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return obj.mobile

# -----------------------------
# User Serializer
# -----------------------------
class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    def get_age(self):
        return ""

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
            "role",
            "role_name",
            "is_staff",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "role_name",
            "created_at",
            "updated_at",
        )


class SendOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


class AddressSerializer(serializers.ModelSerializer):
    pincode = serializers.CharField(source="location.pincode", read_only=True)
    city = serializers.CharField(source="location.city", read_only=True)
    state = serializers.CharField(source="location.state", read_only=True)
    user_mobile = serializers.CharField(source="user.mobile", read_only=True)
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

    def get_user_str(self, obj):
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            mobile = obj.user.mobile or ""
            return f"{first} {last} | {mobile}".strip()
        return ""

    class Meta:
        model = Address
        fields = "__all__"