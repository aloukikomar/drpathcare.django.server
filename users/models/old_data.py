from django.db import models

class OldData(models.Model):
    mobile = models.CharField(max_length=15, db_index=True)
    data = models.JSONField(default=dict)
    source = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.mobile