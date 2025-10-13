from django.db import models


class ContentManager(models.Model):
    """
    Centralized content management for storing media assets (images, docs, etc.)
    Example:
      - Test Image
      - Profile Image
      - Package Banner
    """
    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("pdf", "PDF"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="content/")   # stored in S3 via django-storages
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, default="image")
    tags = models.JSONField(blank=True, null=True)  # flexible metadata storage
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
