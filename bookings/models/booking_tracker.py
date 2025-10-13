import uuid
from django.db import models
from django.conf import settings
from bookings.models import Booking

class BookingActionTracker(models.Model):
    ACTION_CHOICES = [
        ("create", "Created"),
        ("item_update", "Item Updated"),
        ("status_change", "Status Change"),
        ("payment_update", "Payment Update"),
        ("add_item", "Item Added"),
        ("remove_item", "Item Removed"),
        ("cancel", "Cancelled"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="actions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        uname = self.user.email if self.user else "system"
        return f"{self.action} by {uname} on {self.booking.id}"
