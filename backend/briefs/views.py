from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.observability import operation_event
from designs.serializers import DesignSerializer
from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    RoleAwareViewSet,
)

from .models import BriefReferenceUpload, DesignBrief
from .serializers import BriefReferenceUploadSerializer, DesignBriefSerializer
from .services.design_confirmation import DesignConfirmationError, confirm_brief_design
from .services.options import brief_options, is_regional_admin
from .services.prompt_generation import generate_prompt_for_brief


class DesignBriefViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = DesignBrief.objects.select_related("product", "branch", "campaign").all()
    serializer_class = DesignBriefSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "generate_prompt": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "confirm_design": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
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
        operation_event(
            "brief.created",
            brief_id=brief.pk,
            user_id=getattr(creator, "pk", None),
            status=brief.status,
        )

    @action(detail=True, methods=["post"], url_path="generate-prompt")
    def generate_prompt(self, request, pk=None):
        brief = self.get_object()
        generate_prompt_for_brief(brief)
        return Response(self.get_serializer(brief).data)

    @action(detail=True, methods=["post"], url_path="confirm-design")
    def confirm_design(self, request, pk=None):
        brief = self.get_object()
        prompt_text = (
            request.data.get("prompt_override")
            if "prompt_override" in request.data
            else brief.generated_prompt
        )
        try:
            design = confirm_brief_design(brief, prompt_text)
        except DesignConfirmationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            DesignSerializer(design, context=self.get_serializer_context()).data,
            status=201,
        )

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
