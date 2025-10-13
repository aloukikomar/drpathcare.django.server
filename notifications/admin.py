# notification/admin.py
from django.contrib import admin
from .models import Notification, SMSTemplate


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
