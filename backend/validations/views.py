from rest_framework.viewsets import ModelViewSet

from security.permissions import ROLE_DESIGNER, ROLE_PLATFORM_ADMIN, ROLE_REVIEWER, RoleAwareViewSet

from .models import ValidationRun
from .serializers import ValidationRunSerializer


class ValidationRunViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = ValidationRun.objects.select_related("design_version").all()
    serializer_class = ValidationRunSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_DESIGNER, ROLE_REVIEWER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }
