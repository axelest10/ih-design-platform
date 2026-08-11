"""Confirmación del copy y creación de la primera pieza del brief."""
from __future__ import annotations

import json

from ai.providers import AIProviderError, GenerationRequest, OpenAIProvider
from designs.models import Design
from designs.services.renderer import RenderValidationError

from ..models import DesignBrief
from .generation import SUPPORTED_FORMATS, generate_initial_design


class DesignConfirmationError(ValueError):
    """Error controlado que permite reintentar el paso 2 sin crear un diseño parcial."""


def _parse_structured_copy(content: str) -> dict[str, str] | None:
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    copy_fields = {
        "headline": str(payload.get("headline") or "").strip(),
        "body": str(payload.get("body") or "").strip(),
        "cta": str(payload.get("cta") or "").strip(),
        "eyebrow": str(payload.get("eyebrow") or "").strip(),
    }
    if not copy_fields["headline"] or not copy_fields["body"]:
        return None
    return copy_fields


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
    provider = OpenAIProvider()
    copy_fields = None
    try:
        for _attempt in range(2):
            response = provider.generate(generation_request)
            copy_fields = _parse_structured_copy(response.content)
            if copy_fields is not None:
                break
    except AIProviderError as exc:
        raise DesignConfirmationError(
            "No pudimos estructurar el copy en este momento. Intenta de nuevo."
        ) from exc

    if copy_fields is None:
        raise DesignConfirmationError(
            "La propuesta no pudo convertirse en los campos de diseño después de dos intentos."
        )

    try:
        return generate_initial_design(brief, copy_fields)
    except RenderValidationError as exc:
        raise DesignConfirmationError(str(exc)) from exc
