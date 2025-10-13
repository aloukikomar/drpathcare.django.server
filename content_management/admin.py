from django.contrib import admin
from .models import ContentManager


@admin.register(ContentManager)
class ContentManagerAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "media_type", "created_at")
    search_fields = ("title", "description")
    list_filter = ("media_type", "created_at")