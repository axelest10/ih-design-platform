"""Generación inicial para briefs creados desde el formulario general."""
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError, render_preview

from ..models import DesignBrief

SUPPORTED_FORMATS = {
    DesignBrief.Format.SQUARE,
    DesignBrief.Format.STORY,
    DesignBrief.Format.PORTRAIT,
}

CTA_LABELS = {
    "message": "Enviar mensaje",
    "register": "Regístrate",
    "buy": "Compra ahora",
    "information": "Conoce más",
    "visit": "Visita el sitio",
    "event": "Asiste al evento",
}


def _next_test_number() -> int:
    return (
        Design.objects.filter(test_number__isnull=False).aggregate(maximum=Max("test_number"))[
            "maximum"
        ]
        or 0
    ) + 1


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
        test_mode = bool(brief.product_slug and settings.DESIGN_TEST_MODE)
        design = Design.objects.create(
            brief=brief,
            status=(Design.Status.SELF_REVIEW if test_mode else Design.Status.IN_REVIEW),
            test_number=_next_test_number() if test_mode else None,
        )
        DesignVersion.objects.create(
            design=design,
            number=1,
            template_key=rendered.template_key,
            render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
            asset_refs=rendered.asset_refs,
            validation_summary=rendered.validation_summary,
        )
        brief.status = DesignBrief.Status.IN_REVIEW
        brief.save(update_fields=["status", "updated_at"])
        return design
