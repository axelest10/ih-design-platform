from django.conf import settings
from django.db import transaction
from django.db.models import Max
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    RoleAwareViewSet,
)

from .models import Design, DesignVersion
from .serializers import DesignSerializer
from .services.renderer import RenderValidationError, render_preview


class DesignViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = Design.objects.prefetch_related("versions").all()
    serializer_class = DesignSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
        "preview": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "claude_review": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "review": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
    }

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        """Renderiza y versiona un diseño; un resultado válido pasa a revisión."""
        design = self.get_object()
        render_payload = request.data.copy()
        if not render_payload.get("logo_name") and design.brief.brand_logo_key:
            render_payload["logo_name"] = design.brief.brand_logo_key
        if not render_payload.get("additional_logo_keys"):
            render_payload["additional_logo_keys"] = design.brief.additional_logo_keys
        try:
            rendered = render_preview(render_payload)
        except RenderValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

        with transaction.atomic():
            next_number = (
                design.versions.aggregate(max_number=Max("number"))["max_number"] or 0
            ) + 1
            version = DesignVersion.objects.create(
                design=design,
                number=next_number,
                template_key=rendered.template_key,
                render_data=rendered.data,
                asset_refs=rendered.asset_refs,
                validation_summary=rendered.validation_summary,
            )
            update_fields = ["status", "updated_at"]
            if design.brief.product_slug and settings.DESIGN_TEST_MODE:
                if design.test_number is None:
                    latest_test = (
                        Design.objects.filter(test_number__isnull=False).aggregate(
                            max_number=Max("test_number")
                        )["max_number"]
                        or 0
                    )
                    design.test_number = latest_test + 1
                    update_fields.append("test_number")
                design.status = Design.Status.SELF_REVIEW
            else:
                design.status = Design.Status.IN_REVIEW
            design.save(update_fields=update_fields)

        return Response(
            {
                "design_id": str(design.pk),
                "status": design.status,
                "version": version.number,
                "test_number": design.test_number,
                "template_key": rendered.template_key,
                "template_version": rendered.template_version,
                "validation": rendered.validation_summary,
                "test_batch_limit": settings.DESIGN_TEST_LIMIT,
                "test_batch_complete": bool(
                    design.test_number and design.test_number >= settings.DESIGN_TEST_LIMIT
                ),
                "preview": {"html": rendered.html, "svg": rendered.svg},
            },
            status=201,
        )

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """Aprueba o rechaza una versión renderizada del diseño."""
        design = self.get_object()
        if design.brief.product_slug and settings.DESIGN_TEST_MODE:
            return Response(
                {
                    "detail": (
                        "La aprobaciÃ³n formal estÃ¡ desactivada durante las "
                        "primeras 50 pruebas."
                    ),
                    "next": "claude-review",
                },
                status=409,
            )
        decision = request.data.get("decision")
        if decision not in {"approve", "reject"}:
            return Response(
                {"detail": "decision debe ser 'approve' o 'reject'."},
                status=400,
            )

        version_number = request.data.get("version")
        version = (
            design.versions.filter(number=version_number).first()
            if version_number
            else design.versions.first()
        )
        if version is None:
            return Response({"detail": "No existe una versión para revisar."}, status=404)

        if decision == "approve":
            design.status = Design.Status.APPROVED
            design.approved_version = version
        else:
            design.status = Design.Status.REJECTED
        design.save(update_fields=["status", "approved_version", "updated_at"])
        return Response(
            {
                "design_id": str(design.pk),
                "status": design.status,
                "version": version.number,
                "approved_version": design.approved_version_id,
            }
        )

    @action(detail=True, methods=["post"], url_path="claude-review")
    def claude_review(self, request, pk=None):
        """Persiste la revisiÃ³n de calidad de Claude sin convertirla en aprobaciÃ³n humana."""
        design = self.get_object()
        decision = request.data.get("decision")
        if decision not in {"pass", "needs_changes"}:
            return Response(
                {"detail": "decision debe ser 'pass' o 'needs_changes'."}, status=400
            )
        version_number = request.data.get("version")
        version = (
            design.versions.filter(number=version_number).first()
            if version_number
            else design.versions.first()
        )
        if version is None:
            return Response({"detail": "No existe una versiÃ³n para revisar."}, status=404)

        version.claude_review_status = decision
        version.claude_review = request.data.get("report", {})
        version.save(update_fields=["claude_review_status", "claude_review"])
        design.status = (
            Design.Status.TEST_READY
            if decision == "pass"
            else Design.Status.REVISION_REQUESTED
        )
        design.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "design_id": str(design.pk),
                "status": design.status,
                "version": version.number,
                "claude_review_status": version.claude_review_status,
                "report": version.claude_review,
                "test_number": design.test_number,
            }
        )
