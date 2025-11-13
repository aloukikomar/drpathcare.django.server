from rest_framework import serializers
from .models import LabCategory, LabTest, Profile, Package


class LabCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabCategory
        fields = ["id", "name", "entity_type", "description"]


class LabTestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image_url = serializers.CharField(source="image.url", read_only=True)

    class Meta:
        model = LabTest
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image_url = serializers.CharField(source="image.url", read_only=True)
    tests = LabTestSerializer(many=True, read_only=True)
    test_ids = serializers.PrimaryKeyRelatedField(
        queryset=LabTest.objects.all(), many=True, write_only=True, source="tests"
    )

    class Meta:
        model = Profile
        fields = ["id", "name", "description", "category", "category_name","offer_price",
                  "price", "image", "image_url", "tests", "test_ids"]


class PackageSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image_url = serializers.CharField(source="image.url", read_only=True)
    profiles = ProfileSerializer(many=True, read_only=True)
    tests = LabTestSerializer(many=True, read_only=True)

    profile_ids = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(), many=True, write_only=True, source="profiles"
    )
    test_ids = serializers.PrimaryKeyRelatedField(
        queryset=LabTest.objects.all(), many=True, write_only=True, source="tests"
    )

    class Meta:
        model = Package
        fields = ["id", "name", "description", "category", "category_name",
                  "price", "image", "image_url", "profiles", "tests",
                  "profile_ids", "test_ids","offer_price"]