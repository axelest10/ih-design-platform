from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ai.services import persist_design_review
from materials.models import MaterialType
from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    RoleAwareViewSet,
)

from .models import Design, DesignReviewComment, DesignVersion
from .serializers import DesignReviewCommentSerializer, DesignSerializer
from .services.renderer import RenderValidationError, render_preview
from .services.renderer_document import render_document_preview


class DesignViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = Design.objects.select_related(
        "brief", "brief__material_type", "approved_version"
    ).prefetch_related("versions")
    serializer_class = DesignSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "destroy": (ROLE_PLATFORM_ADMIN,),
        "preview": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "claude_review": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
        "review": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
        "comments": (ROLE_PLATFORM_ADMIN, ROLE_REVIEWER),
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
        material_type = design.brief.material_type
        if material_type and material_type.renderer_family == MaterialType.RendererFamily.DOCUMENT:
            return self._preview_document(design, render_payload, material_type)
        if material_type and material_type.renderer_family != MaterialType.RendererFamily.HTML_SVG:
            return Response(
                {
                    "detail": (
                        f"Renderer '{material_type.renderer_family}' todavía no está implementado."
                    )
                },
                status=400,
            )
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
                render_data={
                    **rendered.data,
                    "html": rendered.html,
                    "svg": rendered.svg,
                },
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

    def _preview_document(self, design, render_payload, material_type):
        try:
            rendered = render_document_preview(
                render_payload,
                material_type=material_type,
            )
        except RenderValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

        with transaction.atomic():
            next_number = (
                design.versions.aggregate(max_number=Max("number"))["max_number"] or 0
            ) + 1
            pdf_path = default_storage.save(
                f"generated-designs/{design.pk}/version-{next_number}.pdf",
                ContentFile(rendered.pdf),
            )
            version = DesignVersion.objects.create(
                design=design,
                number=next_number,
                template_key=rendered.template_key,
                render_data={**rendered.data, "pdf_path": pdf_path},
                asset_refs=[*rendered.asset_refs, pdf_path],
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
                "preview": {"pdf_url": default_storage.url(pdf_path)},
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
        comment = str(request.data.get("comment") or "").strip()
        if comment:
            DesignReviewComment.objects.create(
                design=design,
                version=version,
                author=request.user,
                comment=comment,
            )
        return Response(
            {
                "design_id": str(design.pk),
                "status": design.status,
                "version": version.number,
                "approved_version": design.approved_version_id,
            }
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        """Lista o agrega retroalimentación humana sin alterar la decisión formal."""
        design = self.get_object()
        if request.method == "GET":
            comments = design.review_comments.select_related("author", "version").all()
            return Response(DesignReviewCommentSerializer(comments, many=True).data)

        serializer = DesignReviewCommentSerializer(
            data=request.data,
            context={"request": request, "design": design},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(design=design, author=request.user)
        return Response(serializer.data, status=201)

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

        persist_design_review(
            version,
            decision=decision,
            report=request.data.get("report", {}),
            provider="claude-manual",
            automated=False,
        )
        design.refresh_from_db(fields=["status", "updated_at"])
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
