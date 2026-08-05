from rest_framework.viewsets import ModelViewSet

from .models import Design
from .serializers import DesignSerializer


class DesignViewSet(ModelViewSet):
    queryset = Design.objects.prefetch_related("versions").all()
    serializer_class = DesignSerializer
