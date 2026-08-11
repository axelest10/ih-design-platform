import mimetypes
import re
from pathlib import Path

from django.http import FileResponse, Http404
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

MAX_MARKETING_ASSET_BULK_FILES = 30


def _marketing_asset_label(filename):
    stem = Path(filename).stem
    words = re.sub(r"[-_]+", " ", stem).split()
    label = " ".join(
        word
        if word.isupper() or any(character.isdigit() for character in word)
        else word.capitalize()
        for word in words
    )
    return (label or "Material")[:180]


def _serializer_error_message(errors):
    messages = []
    for value in errors.values():
        values = value if isinstance(value, list) else [value]
        messages.extend(str(message) for message in values)
    return "; ".join(messages)


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
        "bulk": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }

    def get_permissions(self):
        if self.action == "file":
            return [AllowAny()]
        return super().get_permissions()

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

    def file(self, request, pk=None, filename=None):
        """Sirve un material desde el storage sin exponer su URL firmada al navegador."""
        asset = self.get_object()
        if not asset.file:
            raise Http404

        try:
            file_handle = asset.file.open("rb")
        except Exception as exc:
            raise Http404 from exc

        content_type, _ = mimetypes.guess_type(asset.file.name)
        response = FileResponse(
            file_handle,
            content_type=content_type or "application/octet-stream",
            filename=Path(asset.file.name).name,
        )
        response["Cache-Control"] = "public, max-age=3600"
        return response

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "Selecciona al menos un archivo."}, status=400)
        if len(files) > MAX_MARKETING_ASSET_BULK_FILES:
            return Response(
                {
                    "detail": (
                        "La carga múltiple permite un máximo de "
                        f"{MAX_MARKETING_ASSET_BULK_FILES} archivos por solicitud."
                    )
                },
                status=400,
            )

        shared_data = {
            "brand": request.data.get("brand", ""),
            "country": request.data.get("country", ""),
            "category": request.data.get("category", ""),
        }
        created = []
        failed = []
        for uploaded_file in files:
            serializer = self.get_serializer(
                data={
                    **shared_data,
                    "label": _marketing_asset_label(uploaded_file.name),
                    "file": uploaded_file,
                }
            )
            if serializer.is_valid():
                asset = serializer.save(uploaded_by=request.user)
                created.append(self.get_serializer(asset).data)
                continue
            failed.append(
                {
                    "filename": uploaded_file.name,
                    "reason": _serializer_error_message(serializer.errors),
                }
            )

        return Response(
            {
                "created_count": len(created),
                "failed_count": len(failed),
                "created": created,
                "failed": failed,
            },
            status=201 if created else 200,
        )


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
