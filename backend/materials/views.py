from rest_framework.viewsets import ModelViewSet

from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    RoleAwareViewSet,
)

from .models import MaterialBundle, MaterialTemplate, MaterialType
from .serializers import (
    MaterialBundleSerializer,
    MaterialTemplateSerializer,
    MaterialTypeSerializer,
)


class MaterialTypeViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialType.objects.prefetch_related("templates").all()
    serializer_class = MaterialTypeSerializer
    http_method_names = ["get", "head", "options"]


class MaterialTemplateViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialTemplate.objects.select_related("material_type").all()
    serializer_class = MaterialTemplateSerializer
    http_method_names = ["get", "head", "options"]


class MaterialBundleViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialBundle.objects.select_related(
        "material_type", "branch", "campaign", "created_by"
    ).prefetch_related("items")
    serializer_class = MaterialBundleSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()
        ):
            queryset = queryset.filter(created_by=user)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
