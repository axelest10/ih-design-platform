from rest_framework.viewsets import ModelViewSet

from .models import DesignBrief
from .serializers import DesignBriefSerializer


class DesignBriefViewSet(ModelViewSet):
    queryset = DesignBrief.objects.select_related("product", "branch", "campaign").all()
    serializer_class = DesignBriefSerializer
