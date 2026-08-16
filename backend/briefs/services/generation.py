"""Generación inicial para briefs creados desde el formulario general."""
from __future__ import annotations

from django.db import transaction

from ai.services import run_automatic_design_review
from designs.models import Design
from designs.services.renderer import RenderValidationError, render_preview
from designs.services.versioning import create_next_version

from ..models import DesignBrief

SUPPORTED_FORMATS = {
    DesignBrief.Format.SQUARE,
    DesignBrief.Format.STORY,
    DesignBrief.Format.PORTRAIT,
}

# These are the only brief formats wired to the current template renderer.
SUPPORTED_BRIEF_FORMATS = frozenset(SUPPORTED_FORMATS)

CTA_LABELS = {
    "message": "Enviar mensaje",
    "register": "Regístrate",
    "buy": "Compra ahora",
    "information": "Conoce más",
    "visit": "Visita el sitio",
    "event": "Asiste al evento",
}


def generate_initial_design(brief: DesignBrief, copy_fields: dict[str, str]) -> Design:
    """Crea la primera versión desde el copy estructurado confirmado por la persona."""
    if brief.format not in SUPPORTED_FORMATS:
        raise RenderValidationError(
            f"El formato '{brief.format}' todavía no tiene una plantilla disponible."
        )

    render_payload = {
        "template_key": f"{brief.format}-v1",
        "headline": str(copy_fields.get("headline") or "").strip(),
        "body": str(copy_fields.get("body") or "").strip(),
        "eyebrow": str(copy_fields.get("eyebrow") or "International House").strip(),
        "logo_name": brief.brand_logo_key,
        "additional_logo_keys": brief.additional_logo_keys,
        "product_slug": brief.product_slug,
        # Igual que quick-design: conserva la alerta de contraste sin bloquear el render.
        "_allow_validation_warnings": True,
    }
    cta = str(copy_fields.get("cta") or "").strip() or CTA_LABELS.get(
        str((brief.brief_data or {}).get("cta") or "").strip(),
        "",
    )
    if cta:
        render_payload["cta"] = cta

    with transaction.atomic():
        rendered = render_preview(render_payload)
        design = Design.objects.create(brief=brief)
        design, version = create_next_version(design, rendered)
        brief.status = DesignBrief.Status.IN_REVIEW
        brief.save(update_fields=["status", "updated_at"])
    run_automatic_design_review(version)
    design.refresh_from_db(fields=["status", "updated_at"])
    return design
