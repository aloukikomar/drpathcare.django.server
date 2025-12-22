from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role,Address,Patient,Location


# -----------------------------
# Role Admin
# -----------------------------
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "view_all")
    search_fields = ("name",)
    list_filter = ("view_all",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    # --------------------------------------------------
    # LIST PAGE
    # --------------------------------------------------
    list_display = (
        "id",
        "email",
        "mobile",
        "first_name",
        "last_name",
        "role",
        "parent",
        "user_code",
        "is_active",
        "created_at",
        
    )

    list_filter = (
        "is_active",
        "role",
        "gender",
    )

    search_fields = (
        "email",
        "mobile",
        "first_name",
        "last_name",
        "user_code",
    )

    ordering = ("-created_at",)

    autocomplete_fields = ("parent",)

    # --------------------------------------------------
    # EDIT PAGE
    # --------------------------------------------------
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "mobile",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "gender",
                    "date_of_birth",
                    "age",
                )
            },
        ),
        (
            "Role & Hierarchy",
            {
                "fields": (
                    "role",
                    "parent",
                    "user_code",
                    "custome_permissions"
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    # --------------------------------------------------
    # ADD USER PAGE
    # --------------------------------------------------
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "mobile",
                    "password1",
                    "password2",
                    "role",
                    "parent",
                    "user_code",
                    "is_active",
                ),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")

    readonly_fields = ("created_at", "updated_at")

    # --------------------------------------------------
    # ADMIN UX IMPROVEMENTS
    # --------------------------------------------------
    def get_queryset(self, request):
        """
        Optimize admin queries
        """
        qs = super().get_queryset(request)
        return qs.select_related("role", "parent")

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