"""Punto único de entrada para registrar revisiones visuales por versión."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.observability import operation_event
from designs.models import Design, DesignVersion

from .audit import record_visual_review
from .routing import AITaskType, ai_router_enabled, select_provider


class VisualReviewProviderError(RuntimeError):
    """El proveedor de revisión no pudo devolver una decisión válida."""


@dataclass(frozen=True)
class VisualReviewRequest:
    version_id: int
    design_id: int
    template_key: str
    render_data: dict[str, Any]
    asset_refs: list[Any]
    validation_summary: dict[str, Any]


@dataclass(frozen=True)
class VisualReviewResult:
    decision: str
    report: dict[str, Any] = field(default_factory=dict)


class VisualReviewProvider(Protocol):
    name: str

    def review(self, request: VisualReviewRequest) -> VisualReviewResult:
        ...


class NeedsConfirmationClaudeReviewProvider:
    """Fallback explícito cuando la integración de Anthropic no está configurada."""

    name = "claude-stub"

    def review(self, request: VisualReviewRequest) -> VisualReviewResult:
        return VisualReviewResult(
            decision=DesignVersion.ClaudeReviewStatus.PENDING,
            report={
                "integration_status": "needs_confirmation",
                "summary": (
                    "La pieza está lista para revisión, pero faltan ANTHROPIC_API_KEY o "
                    "ANTHROPIC_MODEL en el entorno."
                ),
                "template_key": request.template_key,
            },
        )


def _review_request(version: DesignVersion) -> VisualReviewRequest:
    return VisualReviewRequest(
        version_id=version.pk,
        design_id=version.design_id,
        template_key=version.template_key,
        render_data=version.render_data,
        asset_refs=version.asset_refs,
        validation_summary=version.validation_summary,
    )


@transaction.atomic
def persist_design_review(
    version: DesignVersion,
    *,
    decision: str,
    report: dict[str, Any] | None = None,
    provider: str,
    automated: bool,
) -> DesignVersion:
    """Persiste la revisión y aplica las mismas transiciones usadas por el endpoint manual."""
    allowed = set(DesignVersion.ClaudeReviewStatus.values)
    if decision not in allowed:
        raise VisualReviewProviderError(
            f"Estado de revisión inválido '{decision}'; se esperaba uno de {sorted(allowed)}."
        )

    version.claude_review_status = decision
    version.claude_review = {
        **(report or {}),
        "provider": provider,
        "automated": automated,
        "reviewed_at": timezone.now().isoformat(),
    }
    version.save(update_fields=["claude_review_status", "claude_review"])

    design = version.design
    if decision == DesignVersion.ClaudeReviewStatus.PASS:
        design.status = Design.Status.TEST_READY
        design.save(update_fields=["status", "updated_at"])
    elif decision == DesignVersion.ClaudeReviewStatus.NEEDS_CHANGES:
        design.status = Design.Status.REVISION_REQUESTED
        design.save(update_fields=["status", "updated_at"])

    return version


def run_automatic_design_review(
    version: DesignVersion,
    *,
    provider: VisualReviewProvider | None = None,
) -> DesignVersion:
    """Ejecuta Anthropic cuando está configurado o registra un pendiente trazable."""
    route_metadata = None
    if provider is not None:
        selected_provider = provider
    elif ai_router_enabled():
        selection = select_provider(AITaskType.AUTOMATIC_VISUAL_REVIEW)
        selected_provider = selection.provider
        route_metadata = selection.audit_metadata
    else:
        selected_provider = configured_visual_review_provider()
    started_at = perf_counter()
    operation_event(
        "visual_review.started",
        design_id=version.design_id,
        version_id=version.pk,
        provider=selected_provider.name,
        automated=True,
    )
    try:
        result = selected_provider.review(_review_request(version))
    except VisualReviewProviderError as exc:
        record_visual_review(
            provider=selected_provider,
            request=_review_request(version),
            result=None,
            error=exc,
            audit_metadata=route_metadata,
        )
        reviewed = persist_design_review(
            version,
            decision=DesignVersion.ClaudeReviewStatus.PENDING,
            report={
                "integration_status": "provider_error",
                "summary": str(exc),
            },
            provider=selected_provider.name,
            automated=True,
        )
        operation_event(
            "visual_review.completed",
            design_id=version.design_id,
            version_id=version.pk,
            provider=selected_provider.name,
            automated=True,
            status="provider_error",
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        return reviewed

    record_visual_review(
        provider=selected_provider,
        request=_review_request(version),
        result=result,
        audit_metadata=route_metadata,
    )
    reviewed = persist_design_review(
        version,
        decision=result.decision,
        report=result.report,
        provider=selected_provider.name,
        automated=True,
    )
    operation_event(
        "visual_review.completed",
        design_id=version.design_id,
        version_id=version.pk,
        provider=selected_provider.name,
        automated=True,
        status=result.decision,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    return reviewed


def configured_visual_review_provider() -> VisualReviewProvider:
    if getattr(settings, "ANTHROPIC_API_KEY", "") and getattr(
        settings, "ANTHROPIC_MODEL", ""
    ):
        from ai.providers.anthropic_review import AnthropicVisualReviewProvider

        return AnthropicVisualReviewProvider()
    return NeedsConfirmationClaudeReviewProvider()
