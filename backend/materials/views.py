from rest_framework.decorators import action
from rest_framework.response import Response
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
from .services.school_kit import SchoolKitGenerationError, generate_school_kit


class MaterialTypeViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialType.objects.prefetch_related("templates").all()
    serializer_class = MaterialTypeSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class MaterialTemplateViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialTemplate.objects.select_related("material_type").all()
    serializer_class = MaterialTemplateSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class MaterialBundleViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = MaterialBundle.objects.select_related(
        "material_type", "branch", "campaign", "created_by"
    ).prefetch_related("items__brief__design__versions")
    serializer_class = MaterialBundleSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
        "generate": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
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

    @action(detail=True, methods=["post"], url_path="generate")
    def generate(self, request, pk=None):
        bundle = self.get_object()
        try:
            generate_school_kit(
                bundle,
                user=request.user if request.user.is_authenticated else None,
            )
        except SchoolKitGenerationError as exc:
            return Response({"detail": str(exc)}, status=400)
        bundle.refresh_from_db()
        return Response(self.get_serializer(bundle).data, status=201)
