from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    CanCreateBriefPermission,
    CorporateDomainPermission,
    RoleAwareViewSet,
    is_platform_admin_user,
)

from .models import MarketingAsset, MaterialBundle, MaterialTemplate, MaterialType
from .serializers import (
    MarketingAssetSerializer,
    MaterialBundleSerializer,
    MaterialTemplateSerializer,
    MaterialTypeSerializer,
)
from .services.quick_design import QuickDesignError, create_quick_design
from .services.school_kit import SchoolKitGenerationError, generate_school_kit


@api_view(["POST"])
@permission_classes([CorporateDomainPermission, CanCreateBriefPermission])
def quick_design(request):
    """Crea y versiona una pieza real desde los campos editables de un template."""
    try:
        result = create_quick_design(request.data, user=request.user)
    except QuickDesignError as exc:
        return Response({"detail": str(exc)}, status=400)
    return Response(result, status=201)


class PublicCatalogReadMixin:
    """Hace público solo el catálogo no sensible usado por la galería de plantillas."""

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return super().get_permissions()


class MaterialTypeViewSet(PublicCatalogReadMixin, RoleAwareViewSet, ModelViewSet):
    queryset = MaterialType.objects.prefetch_related("templates").all()
    serializer_class = MaterialTypeSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class MaterialTemplateViewSet(PublicCatalogReadMixin, RoleAwareViewSet, ModelViewSet):
    queryset = MaterialTemplate.objects.select_related("material_type").all()
    serializer_class = MaterialTemplateSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class MarketingAssetViewSet(PublicCatalogReadMixin, RoleAwareViewSet, ModelViewSet):
    queryset = MarketingAsset.objects.select_related("uploaded_by").all()
    serializer_class = MarketingAssetSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if not is_platform_admin_user(self.request.user):
            queryset = queryset.filter(active=True)
        for field in ("brand", "country", "category"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


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
