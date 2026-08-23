"""Refinamiento de copy sobre la versión vigente de un diseño."""
from __future__ import annotations

from ai.providers import GenerationRequest, OpenAIProvider
from ai.services import run_automatic_design_review
from designs.models import Design

from .copy_generation import StructuredCopyError, generate_structured_copy
from .renderer import RenderValidationError, render_preview
from .versioning import create_next_version


class DesignRevisionError(ValueError):
    """Error controlado que no debe crear una nueva versión."""


def revise_design(design: Design, instruction: str) -> Design:
    """Aplica una instrucción aislada al copy más reciente y crea otra versión."""
    instruction = str(instruction or "").strip()
    if not instruction:
        raise DesignRevisionError("Escribe qué quieres ajustar antes de pedir el cambio.")

    current_version = design.versions.first()
    if current_version is None:
        raise DesignRevisionError("El diseño todavía no tiene una versión que se pueda ajustar.")

    current = current_version.render_data or {}
    generation_request = GenerationRequest(
        instruction=(
            "Actualiza el copy vigente según la instrucción del usuario y devuelve un objeto "
            "JSON válido con exactamente las claves headline, body, cta y eyebrow. Devuelve "
            "el objeto completo actualizado, no un diff, sin backticks de markdown ni texto "
            "antes o después. headline y body deben ser textos no vacíos. Conserva todo lo "
            "que la instrucción no pida cambiar y no inventes precios, fechas, cupos, contactos, "
            "datos académicos ni logos."
        ),
        authorized_context={
            "current_headline": str(current.get("headline") or ""),
            "current_body": str(current.get("body") or ""),
            "current_cta": str(current.get("cta") or ""),
            "current_eyebrow": str(current.get("eyebrow") or ""),
            "instruction": instruction,
            "product_slug": design.brief.product_slug,
            "channel": design.brief.channel,
            "language": design.brief.language,
        },
        output_format="json",
    )

    try:
        copy_fields = generate_structured_copy(
            OpenAIProvider(), generation_request, design_version=current_version
        )
        rendered = render_preview(
            {
                "template_key": current_version.template_key,
                **copy_fields,
                "logo_name": current.get("logo_name"),
                "additional_logo_keys": current.get("additional_logo_keys", []),
                "product_slug": current.get("product_slug") or design.brief.product_slug,
                "_allow_validation_warnings": True,
            }
        )
    except (StructuredCopyError, RenderValidationError) as exc:
        raise DesignRevisionError(str(exc)) from exc

    design, version = create_next_version(design, rendered)
    run_automatic_design_review(version)
    design.refresh_from_db(fields=["status", "updated_at"])
    return design
