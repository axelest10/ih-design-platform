from rest_framework.serializers import ModelSerializer

from .models import BrandGuideline


class BrandGuidelineSerializer(ModelSerializer):
    class Meta:
        model = BrandGuideline
        fields = "__all__"
