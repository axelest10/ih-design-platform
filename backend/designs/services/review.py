"""Transiciones de revisión humana para una versión de diseño."""
from __future__ import annotations

from django.db import transaction

from designs.models import Design, DesignReviewComment, DesignVersion

from .review_notifications import notify_review_transition


class ReviewTransitionError(ValueError):
    """Indica que una decisión humana no cumple el contrato de revisión."""


class ReviewDecisionLockedError(ReviewTransitionError):
    """Indica que una versión ya tiene una decisión humana definitiva."""


_TRANSITIONS = {
    "approve": (DesignVersion.ReviewStatus.APPROVED, Design.Status.APPROVED),
    "reject": (DesignVersion.ReviewStatus.REJECTED, Design.Status.REJECTED),
    "request_changes": (
        DesignVersion.ReviewStatus.CHANGES_REQUESTED,
        Design.Status.REVISION_REQUESTED,
    ),
}


def transition_design_version(
    *,
    design: Design,
    version: DesignVersion,
    decision: str,
    reviewer,
    comment: str | None = None,
) -> tuple[Design, DesignVersion, DesignReviewComment | None]:
    """Persiste una decisión, su estado y el comentario opcional/obligatorio."""
    if version.design_id != design.pk:
        raise ReviewTransitionError("La versión no pertenece a este diseño.")
    transition = _TRANSITIONS.get(decision)
    if transition is None:
        raise ReviewTransitionError("La decisión de revisión no es válida.")

    normalized_comment = str(comment or "").strip()
    if decision in {"reject", "request_changes"} and not normalized_comment:
        raise ReviewTransitionError("Esta decisión requiere un comentario.")

    version_status, design_status = transition
    with transaction.atomic():
        locked_design = Design.objects.select_for_update().get(pk=design.pk)
        locked_version = DesignVersion.objects.select_for_update().get(pk=version.pk)
        if locked_version.review_status != DesignVersion.ReviewStatus.PENDING:
            raise ReviewDecisionLockedError(
                "La versión ya tiene una decisión de revisión. "
                "Usa la acción explícita de reabrir antes de decidir de nuevo."
            )
        locked_version.review_status = version_status
        locked_version.save(update_fields=["review_status"])

        locked_design.status = design_status
        locked_design.approved_version = locked_version if decision == "approve" else None
        locked_design.save(update_fields=["status", "approved_version", "updated_at"])

        saved_comment = None
        if normalized_comment:
            saved_comment = DesignReviewComment.objects.create(
                design=locked_design,
                version=locked_version,
                author=reviewer,
                comment=normalized_comment,
            )

    notify_review_transition(
        design=locked_design,
        version=locked_version,
        decision=decision,
        comment=saved_comment,
    )
    return locked_design, locked_version, saved_comment


def reopen_design_version(
    *,
    design: Design,
    version: DesignVersion,
    reviewer,
    comment: str | None = None,
) -> tuple[Design, DesignVersion, DesignReviewComment | None]:
    """Reabre una versión decidida y la devuelve al estado pendiente."""
    if version.design_id != design.pk:
        raise ReviewTransitionError("La versión no pertenece a este diseño.")

    normalized_comment = str(comment or "").strip()
    with transaction.atomic():
        locked_design = Design.objects.select_for_update().get(pk=design.pk)
        locked_version = DesignVersion.objects.select_for_update().get(pk=version.pk)
        if locked_version.review_status == DesignVersion.ReviewStatus.PENDING:
            raise ReviewTransitionError("La versión ya está pendiente de una decisión.")

        locked_version.review_status = DesignVersion.ReviewStatus.PENDING
        locked_version.save(update_fields=["review_status"])
        locked_design.status = Design.Status.IN_REVIEW
        locked_design.approved_version = None
        locked_design.save(update_fields=["status", "approved_version", "updated_at"])

        saved_comment = None
        if normalized_comment:
            saved_comment = DesignReviewComment.objects.create(
                design=locked_design,
                version=locked_version,
                author=reviewer,
                comment=normalized_comment,
            )

    notify_review_transition(
        design=locked_design,
        version=locked_version,
        decision="reopen",
        comment=saved_comment,
    )
    return locked_design, locked_version, saved_comment
