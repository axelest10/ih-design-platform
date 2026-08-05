from rest_framework.serializers import ModelSerializer

from .models import ValidationRun


class ValidationRunSerializer(ModelSerializer):
    class Meta:
        model = ValidationRun
        fields = "__all__"
