from rest_framework import serializers
from .models import ContentManager


class ContentManagerSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ContentManager
        fields = ["id", "title", "description", "file", "file_url",
                  "media_type", "tags", "created_at", "updated_at"]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None