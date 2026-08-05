from rest_framework.viewsets import ModelViewSet

from .models import BrandGuideline
from .serializers import BrandGuidelineSerializer


class BrandGuidelineViewSet(ModelViewSet):
    queryset = BrandGuideline.objects.all()
    serializer_class = BrandGuidelineSerializer
