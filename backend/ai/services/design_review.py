"""Punto único de entrada para registrar revisiones visuales por versión."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from django.db import transaction
from django.utils import timezone

from designs.models import Design, DesignVersion


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
    """Stub explícito hasta que Axel confirme API, credenciales y modelo de Claude."""

    name = "claude-stub"

    def review(self, request: VisualReviewRequest) -> VisualReviewResult:
        return VisualReviewResult(
            decision=DesignVersion.ClaudeReviewStatus.PENDING,
            report={
                "integration_status": "needs_confirmation",
                "summary": (
                    "La pieza está lista para revisión, pero la integración real con Claude "
                    "requiere confirmar proveedor, credenciales y modelo."
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
    """Ejecuta el proveedor configurado; por defecto registra el stub pendiente de decisión."""
    selected_provider = provider or NeedsConfirmationClaudeReviewProvider()
    try:
        result = selected_provider.review(_review_request(version))
    except VisualReviewProviderError as exc:
        return persist_design_review(
            version,
            decision=DesignVersion.ClaudeReviewStatus.PENDING,
            report={
                "integration_status": "provider_error",
                "summary": str(exc),
            },
            provider=selected_provider.name,
            automated=True,
        )

    return persist_design_review(
        version,
        decision=result.decision,
        report=result.report,
        provider=selected_provider.name,
        automated=True,
    )
