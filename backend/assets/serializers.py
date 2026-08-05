from rest_framework.serializers import ModelSerializer

from .models import OfficialAsset


class OfficialAssetSerializer(ModelSerializer):
    class Meta:
        model = OfficialAsset
        fields = "__all__"
