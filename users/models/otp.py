from django.db import models
from django.conf import settings
import uuid
from datetime import datetime, timedelta
from django.utils import timezone

class OTP(models.Model):
    mobile = models.CharField(max_length=15, db_index=True,null=True,blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps",null=True,blank=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(minutes=5)  # OTP valid 5 min
        super().save(*args, **kwargs)