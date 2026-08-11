"""Conversión reutilizable de respuestas de IA a copy estructurado."""
from __future__ import annotations

import json

from ai.providers import AIProvider, AIProviderError, GenerationRequest


class StructuredCopyError(ValueError):
    """La IA no pudo devolver un copy estructurado utilizable."""


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


def generate_structured_copy(
    provider: AIProvider,
    generation_request: GenerationRequest,
) -> dict[str, str]:
    """Genera y valida JSON de copy, con un único reintento controlado."""
    try:
        for _attempt in range(2):
            response = provider.generate(generation_request)
            copy_fields = _parse_structured_copy(response.content)
            if copy_fields is not None:
                return copy_fields
    except AIProviderError as exc:
        raise StructuredCopyError(
            "No pudimos estructurar el copy en este momento. Intenta de nuevo."
        ) from exc

    raise StructuredCopyError(
        "La propuesta no pudo convertirse en los campos de diseño después de dos intentos."
    )
