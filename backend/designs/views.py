from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse
from django.utils.cache import patch_cache_control
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ai.services import persist_design_review, run_automatic_design_review
from common.observability import operation_event
from materials.models import MaterialType
from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    CorporateDomainPermission,
    RoleAwareViewSet,
    is_platform_admin_user,
)

from .models import AsyncGenerationJob, Design, DesignReviewComment
from .serializers import DesignReviewCommentSerializer, DesignSerializer
from .services.async_jobs import enqueue_generation_task, task_response
from .services.renderer import RenderValidationError, render_preview
from .services.revision import DesignRevisionError
from .services.versioning import create_next_version
from .tasks import (
    generate_document_preview_task,
    generate_presentation_preview_task,
    revise_design_task,
)


@api_view(["GET"])
@permission_classes([CorporateDomainPermission])
def generation_task_status(request, task_id):
    """Devuelve el estado de una generación sin exponer jobs de otra persona."""
    job = AsyncGenerationJob.objects.filter(task_id=task_id).select_related("owner").first()
    if job is None:
        return Response({"detail": "La tarea solicitada no existe."}, status=404)
    if (
        job.owner_id
        and job.owner_id != getattr(request.user, "pk", None)
        and not is_platform_admin_user(request.user)
    ):
        return Response({"detail": "La tarea solicitada no existe."}, status=404)
    return Response(
        {
            "task_id": job.task_id,
            "kind": job.kind,
            "resource_type": job.resource_type,
            "resource_id": job.resource_id or None,
            "status": job.status,
            "result": job.result if job.status == AsyncGenerationJob.Status.SUCCEEDED else None,
            "error": job.error if job.status == AsyncGenerationJob.Status.FAILED else None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
    )


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
        "revise": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER),
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
        if (
            material_type
            and material_type.renderer_family == MaterialType.RendererFamily.PRESENTATION
        ):
            return self._preview_presentation(design, render_payload, material_type)
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

        design, version = create_next_version(design, rendered)
        run_automatic_design_review(version)
        design.refresh_from_db(fields=["status", "updated_at"])

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

    @action(detail=True, methods=["post"], url_path="revise")
    def revise(self, request, pk=None):
        """Refina el copy vigente mediante una instrucción independiente."""
        design = self.get_object()
        try:
            job = enqueue_generation_task(
                revise_design_task,
                owner=request.user,
                kind="design-revision-copy",
                resource_type="design",
                resource_id=design.pk,
                args=(design.pk, request.data.get("instruction")),
            )
        except DesignRevisionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return task_response(request, job)

    def export_version(self, request, pk=None, version_number=None):
        """Descarga un artefacto persistido de una versión sin regenerarlo."""
        design = self.filter_queryset(self.get_queryset()).filter(pk=pk).first()
        if design is None:
            return Response({"detail": "El diseño solicitado no existe."}, status=404)
        self.check_object_permissions(request, design)
        version = design.versions.filter(number=version_number).first()
        if version is None:
            return Response({"detail": "La versión solicitada no existe."}, status=404)

        output_format = str(request.query_params.get("output") or "svg").strip().lower()
        operation_event(
            "design.version_export",
            design_id=design.pk,
            version_id=version.pk,
            version_number=version.number,
            output=output_format,
            user_id=getattr(request.user, "pk", None),
        )
        filename = f"design-{design.pk}-version-{version.number}.{output_format}"
        inline_artifacts = {
            "svg": ("svg", "image/svg+xml; charset=utf-8"),
            "html": ("html", "text/html; charset=utf-8"),
        }
        stored_artifacts = {
            "pdf": ("pdf_path", "application/pdf"),
            "pptx": (
                "pptx_path",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
        }

        if output_format in inline_artifacts:
            data_key, content_type = inline_artifacts[output_format]
            content = version.render_data.get(data_key)
            if not content:
                return Response(
                    {"detail": f"Esta versión no tiene un archivo {output_format.upper()}."},
                    status=404,
                )
            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            patch_cache_control(response, private=True, no_store=True)
            return response

        if output_format in stored_artifacts:
            data_key, content_type = stored_artifacts[output_format]
            path = version.render_data.get(data_key)
            if not path or not default_storage.exists(path):
                return Response(
                    {"detail": f"Esta versión no tiene un archivo {output_format.upper()}."},
                    status=404,
                )
            response = FileResponse(
                default_storage.open(path, "rb"),
                as_attachment=True,
                filename=filename,
                content_type=content_type,
            )
            patch_cache_control(response, private=True, no_store=True)
            return response

        return Response(
            {"detail": "Formato no disponible. Usa svg, html, pdf o pptx."},
            status=400,
        )

    def _preview_document(self, design, render_payload, material_type):
        try:
            job = enqueue_generation_task(
                generate_document_preview_task,
                owner=self.request.user,
                kind="design-pdf-render",
                resource_type="design",
                resource_id=design.pk,
                args=(design.pk, dict(render_payload), material_type.pk),
            )
        except RenderValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return task_response(self.request, job)

    def _preview_presentation(self, design, render_payload, material_type):
        try:
            job = enqueue_generation_task(
                generate_presentation_preview_task,
                owner=self.request.user,
                kind="design-pptx-render",
                resource_type="design",
                resource_id=design.pk,
                args=(design.pk, dict(render_payload), material_type.pk),
            )
        except RenderValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return task_response(self.request, job)

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
