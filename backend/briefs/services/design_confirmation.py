"""Confirmación del copy y creación de la primera pieza del brief."""
from __future__ import annotations

from ai.providers import GenerationRequest, OpenAIProvider
from designs.models import Design
from designs.services.copy_generation import StructuredCopyError, generate_structured_copy
from designs.services.renderer import RenderValidationError

from ..models import DesignBrief
from .generation import SUPPORTED_FORMATS, generate_initial_design

# generated_prompt is editable advertising copy, not an image-generation prompt.


class DesignConfirmationError(ValueError):
    """Error controlado que permite reintentar el paso 2 sin crear un diseño parcial."""


def confirm_brief_design(brief: DesignBrief, prompt_text: str) -> Design:
    """Estructura el copy confirmado y crea el Design de forma transaccional."""
    if brief.format not in SUPPORTED_FORMATS:
        raise DesignConfirmationError(
            f"El formato '{brief.format}' todavía no tiene una plantilla disponible."
        )
    if Design.objects.filter(brief=brief).exists():
        raise DesignConfirmationError("Este brief ya tiene un diseño generado.")

    confirmed_prompt = str(prompt_text or "").strip()
    if not confirmed_prompt:
        raise DesignConfirmationError("Escribe o genera un copy antes de crear la pieza.")

    brief_data = brief.brief_data or {}
    generation_request = GenerationRequest(
        instruction=(
            "Convierte el copy confirmado en un objeto JSON válido con exactamente las claves "
            "headline, body, cta y eyebrow. Devuelve solo el objeto JSON, sin backticks de "
            "markdown ni texto antes o después. headline y body deben ser textos no vacíos. "
            "Mantén el idioma y la intención del copy confirmado. No inventes precios, fechas, "
            "cupos, contactos, datos académicos ni logos."
        ),
        authorized_context={
            "confirmed_prompt": confirmed_prompt,
            "product_slug": brief.product_slug,
            "channel": brief.channel,
            "language": brief.language,
            "cta_type": brief_data.get("cta", ""),
        },
        output_format="json",
    )
    try:
        copy_fields = generate_structured_copy(OpenAIProvider(), generation_request)
    except StructuredCopyError as exc:
        raise DesignConfirmationError(str(exc)) from exc

    try:
        return generate_initial_design(brief, copy_fields)
    except RenderValidationError as exc:
        raise DesignConfirmationError(str(exc)) from exc
