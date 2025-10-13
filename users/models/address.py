from django.db import models
from django.conf import settings

# -----------------------------
# Address Model
# -----------------------------

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    location = models.ForeignKey('Location', on_delete=models.PROTECT, related_name="addresses",blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.line1}, {self.location}"
    

class Location(models.Model):
    pincode = models.CharField(max_length=10, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=50, default="India")

    def __str__(self):
        return f"{self.city}, {self.state} - {self.pincode}"