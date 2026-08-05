from rest_framework.serializers import ModelSerializer

from .models import Design, DesignVersion


class DesignVersionSerializer(ModelSerializer):
    class Meta:
        model = DesignVersion
        fields = "__all__"


class DesignSerializer(ModelSerializer):
    versions = DesignVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Design
        fields = "__all__"
