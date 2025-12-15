# payments/models.py
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField 

from bookings.models import Booking
from users.models import User

class BookingPayment(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("online", "Online"),
        ("upi", "UPI"),
        ("card", "Card"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True, null=True)

    # 📎 Razorpay / Payment Gateway details
    payment_link = models.URLField(max_length=500, null=True, blank=True, help_text="Payment link generated for the customer.")
    gateway_payment_id = models.CharField(max_length=255, null=True, blank=True, help_text="Payment ID from gateway (e.g. Razorpay payment ID)")
    gateway_order_id = models.CharField(max_length=255, null=True, blank=True, help_text="Order ID or reference from gateway")
    gateway_response = models.JSONField(null=True, blank=True, help_text="Raw gateway response payload for audits and reconciliation")

    remarks = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    file_url = models.URLField(max_length=1024,blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.status} - ₹{self.amount} for Booking {self.booking_id}"


class AgentIncentive(models.Model):
    agent = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="incentives"
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="incentives"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remark = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("agent", "booking")  # optional restriction
        ordering = ["-created_at","agent__first_name"]

    def __str__(self):
        return f"{self.user} → {self.booking} → {self.amount}"
