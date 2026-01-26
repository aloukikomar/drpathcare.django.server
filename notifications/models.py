from django.db import models
from users.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)
    
    # Generic relation to any object (booking, payment, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} to {self.recipient} ({self.status})"


class SMSTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. "login_otp"
    message = models.TextField(
        help_text="Template text. Use placeholders like {otp} or {name}"
    )
    sender_name = models.CharField(max_length=20, default="DPATHC")
    sms_type = models.CharField(max_length=20, default="TRANS")
    peid = models.CharField(max_length=50)
    template_id = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Enquiry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="enquiry"
    )
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    enquiry = models.TextField()
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        default=40,
        related_name="agent_enquiry"
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.mobile})"



class PushDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    expo_push_token = models.CharField(max_length=255, unique=True)

    role = models.CharField(max_length=50, blank=True, null=True)

    platform = models.CharField(
        max_length=20,
        choices=[("android", "Android"), ("ios", "iOS")],
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} · {self.platform}"
