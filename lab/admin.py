from django.contrib import admin
from .models import LabCategory, LabTest, Profile, Package


@admin.register(LabCategory)
class LabCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "entity_type")
    search_fields = ("name",)
    list_filter = ("entity_type",)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("id", "test_code", "name", "category", "price", "reported_on")
    search_fields = ("name", "test_code", "investigation", "sample_type")
    list_filter = ("category", "sample_type", "reported_on")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "category")
    search_fields = ("name",)
    list_filter = ("category",)
    filter_horizontal = ("tests",)


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "category")
    search_fields = ("name",)
    list_filter = ("category",)
    filter_horizontal = ("profiles", "tests")