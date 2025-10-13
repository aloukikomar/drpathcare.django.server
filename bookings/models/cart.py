import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # optional: a name or device/session id could be added

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart {self.id} ({self.user})"

    def recalc_totals(self):
        """Return totals for cart (base_total, offer_total). Do not persist to cart (stateless here)."""
        items = self.items.all()
        base_total = sum((item.base_price or Decimal("0.00")) for item in items)
        offer_total = sum((item.offer_price if item.offer_price is not None else item.base_price or Decimal("0.00"))
                          for item in items)
        return base_total, offer_total


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    patient = models.ForeignKey("users.Patient", on_delete=models.CASCADE, related_name="cart_items")
    lab_test = models.ForeignKey("lab.LabTest", on_delete=models.SET_NULL, null=True, blank=True, related_name="cart_items")
    profile = models.ForeignKey("lab.Profile", on_delete=models.SET_NULL, null=True, blank=True, related_name="cart_items")
    package = models.ForeignKey("lab.Package", on_delete=models.SET_NULL, null=True, blank=True, related_name="cart_items")

    quantity = models.PositiveIntegerField(default=1)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        ref = self.lab_test or self.profile or self.package
        return f"CartItem {self.id} for Cart {self.cart.id} - {ref}"

    def populate_snapshot_prices(self):
        """
        Fill base_price and offer_price from referenced object if not provided.
        Use same logic as BookingItem.
        """
        # only set if not provided or zero
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
        self.populate_snapshot_prices()
        super().save(*args, **kwargs)