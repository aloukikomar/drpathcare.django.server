import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from bookings.models.coupons import Coupon
from users.models import Address  # adjust if different


class Booking(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("verified", "Verified"),
        ("root_manager","Root Manager"),
        ("feild_agent_assigned", "Feild Agent Assigned"),
        ("payment_collected", "Payment Collected"),
        ("sample_collected", "Sample Collected"),
        ("report_uploaded", "Report Uploaded"),
        ("health_manger_assigned", "Health Manger Assigned"),
        ("dietitian_assigned", "Dietitian Assigned"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    CUSTOMER_STATUS_CHOICES = [
        ("registered", "Registered"),
        ("verified", "Verified"),
        ("payment_collected", "Payment Collected"),
        ("sample_collected", "Sample Collected"),
        ("report_uploaded", "Report Uploaded"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("not_required", "Not Required"),
        ("pending", "Pending"),
        ("initiated", "Initiated"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("online", "Online"),
        ("upi", "UPI"),
        ("card", "Card"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ref_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Human-readable reference ID (e.g., DP2510080001)"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    # NEW FIELD — supports multiple users per booking
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="booking_roles",
        help_text="All users associated with this booking (agent, manager, dietitian, etc.)"
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    # 🧮 Calculated totals
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    base_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    offer_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_savings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    admin_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    initial_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="open")
    customer_status = models.CharField(max_length=30, choices=CUSTOMER_STATUS_CHOICES, default="registered")
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)

    scheduled_date = models.DateField(null=True, blank=True)

    # 🆕 Replaced scheduled_time
    scheduled_time_slot = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Example: '6-8 AM', '10-12 AM', or custom text"
    )

    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking {self.id} ({self.user})"
