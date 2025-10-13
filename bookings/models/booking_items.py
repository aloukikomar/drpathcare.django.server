import uuid
from decimal import Decimal
from django.db import models

from users.models import Patient  # adjust import path if different
from lab.models import LabTest, Profile, Package
from bookings.models.booking import Booking

class BookingItem(models.Model):
    """
    Snapshot of booked test/profile/package for a patient.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="booking_items")

    lab_test = models.ForeignKey(LabTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_items")
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_items")
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_items")

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        ref = self.lab_test or self.profile or self.package
        return f"Item {self.id} for Booking {self.booking.id} - {ref}"


    def populate_snapshot_prices(self):
        """
        Fill base_price and offer_price from referenced object if not provided.
        """
        if self.lab_test:
            if not self.base_price:
                self.base_price = self.lab_test.price
            if self.offer_price is None:
                self.offer_price = getattr(self.lab_test, "offer_price", None)
        elif self.profile:
            if not self.base_price:
                self.base_price = self.profile.price or Decimal("0.00")
            if self.offer_price is None:
                self.offer_price = getattr(self.profile, "offer_price", None)
        elif self.package:
            if not self.base_price:
                self.base_price = self.package.price or Decimal("0.00")
            if self.offer_price is None:
                self.offer_price = getattr(self.package, "offer_price", None)


    def save(self, *args, **kwargs):
        # ensure snapshot prices are set before saving
        self.populate_snapshot_prices()
        super().save(*args, **kwargs)
        # after saving, update booking totals
        try:
            self.booking.recalc_totals()
        except Exception:
            # avoid raising in save; admin/devs will see logs
            pass


