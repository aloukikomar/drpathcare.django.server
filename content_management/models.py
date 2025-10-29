from django.db import models


class ContentManager(models.Model):
    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("pdf", "PDF"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_url = models.URLField(max_length=1024, blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, default="image")
    tags = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
