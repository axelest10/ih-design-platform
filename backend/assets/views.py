import json
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from briefs.services.options import is_regional_admin
from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    RoleAwareViewSet,
)

from .models import ArtworkReference, OfficialAsset, UploadedLogo
from .serializers import ArtworkReferenceSerializer, OfficialAssetSerializer, UploadedLogoSerializer


class OfficialAssetViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = OfficialAsset.objects.all()
    serializer_class = OfficialAssetSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class UploadedLogoViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = UploadedLogo.objects.select_related("created_by").all()
    serializer_class = UploadedLogoSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
        "update": (ROLE_PLATFORM_ADMIN,),
        "partial_update": (ROLE_PLATFORM_ADMIN,),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not is_regional_admin(user):
            queryset = queryset.filter(created_by=user)
        return queryset

    def perform_create(self, serializer):
        creator = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=creator)


class ArtworkReferenceViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = ArtworkReference.objects.select_related("created_by").all()
    serializer_class = ArtworkReferenceSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_REVIEWER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_REVIEWER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
        "approve": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
        "reject": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        for field in ("reference_type", "approval_status", "country", "brand_scope", "format"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    @action(detail=False, methods=["get"])
    def knowledge(self, request):
        """Returns the technical visual knowledge base with optional exact filters."""
        knowledge_path = (
            Path(settings.BASE_DIR)
            / "brand"
            / "knowledge"
            / "artwork-reference-knowledge.json"
        )
        if not knowledge_path.exists():
            return Response(
                {"detail": "La base de conocimiento visual no está disponible."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
        assets = knowledge.get("assets", [])

        # Filtros exactos sobre campos planos del asset.
        for field in (
            "country",
            "media_type",
            "format",
            "product_slug",
            "content_pillar",
            "campaign_or_theme",
            "annotation_status",
        ):
            value = request.query_params.get(field)
            if value:
                assets = [asset for asset in assets if asset.get(field) == value]

        # Filtros anidados: se exponen como query params con punto literal
        # (?orientation=, ?calendar.year=, ?calendar.month=) en vez de sintaxis de filtro
        # anidada, para mantener la API simple; cada uno se resuelve contra su ruta interna.
        orientation = request.query_params.get("orientation")
        if orientation:
            assets = [
                asset
                for asset in assets
                if asset.get("technical", {}).get("orientation") == orientation
            ]
        calendar_year = request.query_params.get("calendar.year")
        if calendar_year:
            assets = [
                asset
                for asset in assets
                if str(asset.get("calendar", {}).get("year")) == calendar_year
            ]
        calendar_month = request.query_params.get("calendar.month")
        if calendar_month:
            assets = [
                asset
                for asset in assets
                if str(asset.get("calendar", {}).get("month")) == calendar_month
            ]

        tag = request.query_params.get("tag")
        if tag:
            assets = [asset for asset in assets if tag in asset.get("tags", [])]

        limit = min(int(request.query_params.get("limit", 100)), 500)
        return Response(
            {
                "schema": knowledge.get("schema"),
                "schema_version": knowledge.get("schema_version"),
                "purpose": knowledge.get("purpose"),
                "selection_dimensions": knowledge.get("selection_dimensions", []),
                "summary": {**knowledge.get("summary", {}), "returned_assets": len(assets)},
                "assets": assets[:limit],
            }
        )

    def perform_create(self, serializer):
        creator = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=creator)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        reference = self.get_object()
        reference.approval_status = ArtworkReference.ApprovalStatus.APPROVED
        reference.save(update_fields=["approval_status", "updated_at"])
        return Response(self.get_serializer(reference).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        reference = self.get_object()
        reference.approval_status = ArtworkReference.ApprovalStatus.REJECTED
        reference.save(update_fields=["approval_status", "updated_at"])
        return Response(self.get_serializer(reference).data)
