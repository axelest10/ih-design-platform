from rest_framework.viewsets import ModelViewSet

from security.permissions import ROLE_MARKETING, ROLE_PLATFORM_ADMIN, RoleAwareViewSet

from .models import Campaign
from .serializers import CampaignSerializer


class CampaignViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }
