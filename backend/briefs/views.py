from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    RoleAwareViewSet,
)

from .models import BriefReferenceUpload, DesignBrief
from .serializers import BriefReferenceUploadSerializer, DesignBriefSerializer
from .services.generation import generate_initial_design
from .services.options import brief_options, is_regional_admin


class DesignBriefViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = DesignBrief.objects.select_related("product", "branch", "campaign").all()
    serializer_class = DesignBriefSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not is_regional_admin(user):
            queryset = queryset.filter(created_by=user)
        return queryset

    def perform_create(self, serializer):
        creator = self.request.user if self.request.user.is_authenticated else None
        brief = serializer.save(created_by=creator)
        generate_initial_design(brief)

    @action(detail=False, methods=["get"])
    def options(self, request):
        return Response(brief_options(request.user, request.query_params.get("country")))


class BriefReferenceUploadViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = BriefReferenceUpload.objects.select_related("brief", "created_by").all()
    serializer_class = BriefReferenceUploadSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not is_regional_admin(user):
            queryset = queryset.filter(created_by=user)
        brief_id = self.request.query_params.get("brief")
        if brief_id:
            queryset = queryset.filter(brief_id=brief_id)
        return queryset

    def perform_create(self, serializer):
        creator = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=creator)
