# bookings/models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ("percent", "Percentage"),
        ("flat", "Flat amount"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,
                                         help_text="If percent, store 10 for 10%. If flat, store absolute amount.")
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                              help_text="Cap for percentage discounts, optional.")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True,
                                              help_text="Global usage count limit across all users")
    per_user_limit = models.PositiveIntegerField(null=True, blank=True,
                                                 help_text="How many times single user can use")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_valid_now(self):
        now = timezone.now()
        if not self.active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True

    def remaining_global_uses(self):
        if self.usage_limit is None:
            return None
        used = self.redemptions.count()
        return max(self.usage_limit - used, 0)


class CouponRedemption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_redemptions")
    booking = models.ForeignKey("Booking", on_delete=models.SET_NULL, null=True, blank=True, related_name="coupon_redemptions")
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("coupon", "user", "booking")  # one redemption record per booking per user-coupon