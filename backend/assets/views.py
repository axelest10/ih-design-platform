from rest_framework.viewsets import ModelViewSet

from .models import OfficialAsset
from .serializers import OfficialAssetSerializer


class OfficialAssetViewSet(ModelViewSet):
    queryset = OfficialAsset.objects.all()
    serializer_class = OfficialAssetSerializer
