from rest_framework.viewsets import ModelViewSet

from .models import ValidationRun
from .serializers import ValidationRunSerializer


class ValidationRunViewSet(ModelViewSet):
    queryset = ValidationRun.objects.select_related("design_version").all()
    serializer_class = ValidationRunSerializer
