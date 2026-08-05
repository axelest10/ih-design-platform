from rest_framework.viewsets import ModelViewSet

from .models import Campaign
from .serializers import CampaignSerializer


class CampaignViewSet(ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
