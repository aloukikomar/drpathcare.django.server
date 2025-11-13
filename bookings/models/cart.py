import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class Cart(models.Model):
    """A single active cart per user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(  # ✅ One cart per user
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart ({self.user.mobile})"

    @property
    def total_price(self):
        return sum((item.offer_price or item.base_price or Decimal("0.00")) for item in self.items.all())

    @property
    def total_items(self):
        return self.items.count()


class CartItem(models.Model):
    """An item in the user's cart."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")

    product_type = models.CharField(
        max_length=50,
        choices=[
            ("lab_test", "Lab Test"),
            ("profile", "Profile"),
            ("package", "Package"),
        ]
    )
    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=255)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product_type", "product_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_name} ({self.product_type})"

    @property
    def effective_price(self):
        return self.offer_price or self.base_price
