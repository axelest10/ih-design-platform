"""Utilidades compartidas para APIs de chat compatibles con el SDK de OpenAI."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .base import AIProviderError, GenerationRequest, GenerationResponse

ClientFactory = Callable[..., Any]


def default_client_factory(**kwargs):
    from openai import OpenAI

    return OpenAI(**kwargs)


def _retry_after(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        return headers.get("retry-after") or headers.get("Retry-After")
    except AttributeError:
        return None


def _status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _usage_metadata(usage: Any) -> Any:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    model_dump = getattr(usage, "model_dump", None)
    return model_dump() if callable(model_dump) else None


def generate_with_openai_compatible_client(
    *,
    provider_name: str,
    provider_label: str,
    base_url: str,
    api_key: str,
    model: str,
    request: GenerationRequest,
    client_factory: ClientFactory,
) -> GenerationResponse:
    """Ejecuta una sola llamada de chat; los reintentos pertenecen al router futuro."""
    request_data = {
        "instruction": request.instruction,
        "authorized_context": request.authorized_context,
        "output_format": request.output_format,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "Trabaja solo con el contexto autorizado. No inventes precios, fechas, "
                "ubicaciones, contactos, datos académicos, logos ni claims comerciales."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(request_data, ensure_ascii=False),
        },
    ]
    try:
        client = client_factory(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
        )
        response = client.chat.completions.create(model=model, messages=messages)
    except Exception as exc:
        if _status_code(exc) == 429:
            retry_after = _retry_after(exc)
            retry_detail = f"; retry-after={retry_after}" if retry_after else ""
            raise AIProviderError(
                f"{provider_label} rechazó la generación con HTTP 429{retry_detail}."
            ) from exc
        raise AIProviderError(
            f"{provider_label} no pudo completar la generación."
        ) from exc

    choices = getattr(response, "choices", None)
    if not choices:
        raise AIProviderError(f"{provider_label} no devolvió candidatos de generación.")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content:
        raise AIProviderError(f"{provider_label} no devolvió contenido de texto.")
    metadata = {
        "response_id": getattr(response, "id", None),
        "actual_model": getattr(response, "model", None),
        "usage": _usage_metadata(getattr(response, "usage", None)),
    }
    return GenerationResponse(
        provider=provider_name,
        model=model,
        content=content,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )
