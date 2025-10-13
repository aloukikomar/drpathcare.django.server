from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role,Address,Patient,Location


# -----------------------------
# Role Admin
# -----------------------------
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    list_filter = ("parent",)


# -----------------------------
# User Admin
# -----------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Columns shown in the user list
    list_display = (
        "email",
        "mobile",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "role", "gender")
    search_fields = ("email", "mobile", "first_name", "last_name")
    ordering = ("-created_at",)

    # Fieldsets for edit page
    fieldsets = (
        (None, {"fields": ("email", "mobile", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "gender", "date_of_birth", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        # ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # Fieldsets for add user page
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "mobile", "password1", "password2", "role", "is_staff", "is_active"),
            },
        ),
    )


class PatientInline(admin.TabularInline):
    model = Patient
    extra = 0

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "user", "gender", "date_of_birth")
    search_fields = ("first_name", "last_name", "user__email")
    list_filter = ("gender",)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "line1", "line2", "location", "is_default")
    list_filter = ("is_default", "location__state", "location__city")
    search_fields = ("user__first_name", "user__last_name", "user__email", "line1", "line2")
    autocomplete_fields = ("user", "location")
    ordering = ("user",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("pincode", "city", "state", "country")
    search_fields = ("pincode", "city", "state", "country")
    ordering = ("city", "state")