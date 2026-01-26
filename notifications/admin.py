# notification/admin.py
from django.contrib import admin
from .models import Notification, SMSTemplate,Enquiry, PushDevice


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "sender_name", "sms_type", "peid", "template_id", "is_active")
    search_fields = ("name", "message", "template_id", "peid")
    list_filter = ("is_active", "sms_type", "sender_name")
    ordering = ("name",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "recipient", "status", "created_at", "subject")
    search_fields = ("recipient__username", "recipient__email", "message", "error_message")
    list_filter = ("notification_type", "status", "created_at")
    readonly_fields = ("created_at", "updated_at", "error_message")

    def has_add_permission(self, request):
        # Prevent adding notifications manually (system generated only)
        return False


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "mobile", "created_at")
    search_fields = ("name", "mobile", "enquiry")
    ordering = ("-created_at",)

@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "role",
        "platform",
        "short_token",
        "is_active",
        "created_at",
    )

    list_filter = (
        "platform",
        "role",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__mobile",
        "expo_push_token",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "User Info",
            {
                "fields": ("user", "role", "platform", "is_active"),
            },
        ),
        (
            "Push Token",
            {
                "fields": ("expo_push_token",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def short_token(self, obj):
        return obj.expo_push_token[:30] + "..."

    short_token.short_description = "Expo Token"