"""Creación rápida de piezas que conserva el pipeline Brief → Design → DesignVersion."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max

from ai.services import run_automatic_design_review
from briefs.models import DesignBrief
from briefs.services.options import (
    PRIMARY_PRODUCT_SLUGS,
    validate_brief_logo_access,
    validate_uploaded_logo_access,
)
from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError, render_preview
from designs.services.renderer_document import render_document_preview
from designs.services.renderer_presentation import render_presentation_preview

from ..models import MaterialTemplate, MaterialType


class QuickDesignError(ValueError):
    """El template o el contenido no permiten crear una pieza válida."""


def _validate_logos(payload: dict[str, Any], user) -> tuple[str, list[str]]:
    country = str(payload.get("country") or "").strip()
    logo_name = str(payload.get("brand_logo_key") or "").strip()
    if not country or not logo_name:
        raise QuickDesignError("Selecciona un país y un logo IH aprobado.")
    error = validate_brief_logo_access(logo_name, country, user)
    if error:
        raise QuickDesignError(error)
    additional = [str(key) for key in payload.get("additional_logo_keys") or []]
    if len(additional) > 3:
        raise QuickDesignError("Puedes agregar hasta tres logos adicionales.")
    for key in additional:
        if key.startswith("uploaded:"):
            if not validate_uploaded_logo_access(key.split(":", 1)[1], user):
                raise QuickDesignError(f"No puedes usar el logo subido '{key}'.")
        else:
            error = validate_brief_logo_access(key, country, user)
            if error:
                raise QuickDesignError(error)
    return logo_name, additional


def _next_test_number() -> int:
    return (
        Design.objects.filter(test_number__isnull=False).aggregate(maximum=Max("test_number"))[
            "maximum"
        ]
        or 0
    ) + 1


def _render(template: MaterialTemplate, payload: dict[str, Any]):
    render_payload = {
        "template_key": template.key,
        "product_slug": str(payload.get("product_slug") or ""),
        "logo_name": payload["brand_logo_key"],
        "additional_logo_keys": payload.get("additional_logo_keys") or [],
        "_allow_validation_warnings": True,
        **{field: payload.get(field) for field in template.required_fields},
    }
    family = template.material_type.renderer_family
    if family == MaterialType.RendererFamily.HTML_SVG:
        return family, render_preview(render_payload)
    if family == MaterialType.RendererFamily.DOCUMENT:
        return family, render_document_preview(
            render_payload,
            material_type=template.material_type,
        )
    if family == MaterialType.RendererFamily.PRESENTATION:
        return family, render_presentation_preview(
            render_payload,
            material_type=template.material_type,
        )
    raise QuickDesignError(f"El renderer '{family}' todavía no permite creación rápida.")


@transaction.atomic
def create_quick_design(payload: dict[str, Any], *, user=None) -> dict[str, Any]:
    template_key = str(payload.get("template_key") or "").strip()
    template = (
        MaterialTemplate.objects.filter(key=template_key, active=True)
        .select_related("material_type")
        .first()
    )
    if template is None or not template.material_type.active:
        raise QuickDesignError("La plantilla seleccionada no está disponible.")
    if template.material_type.slug == "school-kit":
        raise QuickDesignError("La paquetería escolar se crea desde su flujo especializado.")

    product_slug = str(payload.get("product_slug") or "").strip()
    if product_slug and product_slug not in PRIMARY_PRODUCT_SLUGS:
        raise QuickDesignError("Selecciona un producto principal válido.")
    logo_name, additional_logo_keys = _validate_logos(payload, user)
    content = {field: str(payload.get(field) or "").strip() for field in template.required_fields}
    missing = [field for field, value in content.items() if not value]
    if missing:
        raise QuickDesignError("Faltan campos obligatorios: " + ", ".join(missing) + ".")

    normalized_payload = {
        **payload,
        **content,
        "brand_logo_key": logo_name,
        "additional_logo_keys": additional_logo_keys,
    }
    try:
        family, rendered = _render(template, normalized_payload)
    except RenderValidationError as exc:
        raise QuickDesignError(str(exc)) from exc

    title = content.get("headline") or content.get("name") or template.key
    design_format = template.constraints.get("format") or DesignBrief.Format.HTML
    brief = DesignBrief.objects.create(
        status=DesignBrief.Status.IN_REVIEW,
        format=design_format,
        title=title[:180],
        country=str(payload.get("country") or ""),
        product_slug=product_slug,
        brand_logo_key=logo_name,
        additional_logo_keys=additional_logo_keys,
        material_type=template.material_type,
        audience=str(payload.get("audience") or "Audiencia definida por el equipo de marketing"),
        objective=str(payload.get("objective") or "Crear una pieza con la plantilla seleccionada"),
        requested_message=title,
        channel=template.material_type.channel,
        brief_data={
            "source": "quick-design",
            "template_key": template.key,
            "content": content,
        },
        constraints={"source": "quick-design", "template_key": template.key},
        created_by=user if user and user.is_authenticated else None,
    )
    design = Design.objects.create(
        brief=brief,
        status=(
            Design.Status.SELF_REVIEW
            if product_slug and settings.DESIGN_TEST_MODE
            else Design.Status.IN_REVIEW
        ),
        test_number=(
            _next_test_number() if product_slug and settings.DESIGN_TEST_MODE else None
        ),
    )
    render_data = dict(rendered.data)
    asset_refs = list(rendered.asset_refs)
    if family == MaterialType.RendererFamily.HTML_SVG:
        render_data.update({"html": rendered.html, "svg": rendered.svg})
        preview = {"html": rendered.html, "svg": rendered.svg}
    elif family == MaterialType.RendererFamily.DOCUMENT:
        path = default_storage.save(
            f"generated-designs/{design.pk}/version-1.pdf",
            ContentFile(rendered.pdf),
        )
        render_data["pdf_path"] = path
        asset_refs.append(path)
        preview = {"pdf_url": default_storage.url(path)}
    else:
        path = default_storage.save(
            f"generated-designs/{design.pk}/version-1.pptx",
            ContentFile(rendered.pptx),
        )
        render_data["pptx_path"] = path
        asset_refs.append(path)
        preview = {"pptx_url": default_storage.url(path)}

    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key=rendered.template_key,
        render_data=render_data,
        asset_refs=asset_refs,
        validation_summary=rendered.validation_summary,
    )
    run_automatic_design_review(version)
    design.refresh_from_db(fields=["status", "updated_at"])
    return {
        "design_id": str(design.pk),
        "brief_id": str(brief.pk),
        "status": design.status,
        "version": version.number,
        "template_key": template.key,
        "validation": rendered.validation_summary,
        "preview": preview,
    }
