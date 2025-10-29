from rest_framework import serializers
from .models import ContentManager


class ContentManagerSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentManager
        fields = '__all__'
