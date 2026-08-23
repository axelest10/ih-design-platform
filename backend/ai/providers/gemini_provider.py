"""Adaptador REST de Gemini reservado para evaluaciones con datos no sensibles."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from .base import AIProviderError, GenerationRequest, GenerationResponse

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _read_http_error(exc: HTTPError) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return None, None
    status = error.get("status")
    message = error.get("message")
    return (
        status if isinstance(status, str) else None,
        message if isinstance(message, str) else None,
    )


def _default_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS origin
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        status, message = _read_http_error(exc)
        detail = ": ".join(part for part in (status, message) if part)
        suffix = f" ({detail})" if detail else ""
        raise AIProviderError(
            f"Gemini rechazó la generación con HTTP {exc.code}{suffix}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise AIProviderError("Gemini no respondió dentro del tiempo permitido.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AIProviderError("Gemini devolvió una respuesta no válida.") from exc


def _generate_content_url(model: str) -> str:
    model_id = model.removeprefix("models/")
    return f"{GEMINI_API_BASE_URL}/models/{quote(model_id, safe='')}:generateContent"


def _response_text(response: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AIProviderError("Gemini no devolvió candidatos de generación.")
    candidate = candidates[0]
    content = candidate.get("content") if isinstance(candidate, dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise AIProviderError("Gemini no devolvió contenido de texto.")
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    if not text:
        raise AIProviderError("Gemini no devolvió contenido de texto.")
    metadata = {
        "response_id": response.get("responseId"),
        "model_version": response.get("modelVersion"),
        "finish_reason": candidate.get("finishReason"),
        "usage_metadata": response.get("usageMetadata"),
    }
    return text, {key: value for key, value in metadata.items() if value is not None}


class GeminiProvider:
    """Proveedor exclusivo para evaluación con datos sintéticos o públicos.

    Los servicios gratuitos de Gemini pueden usar el contenido enviado y las respuestas para
    mejorar productos y tecnologías de Google, y sus términos contemplan revisión humana
    (https://ai.google.dev/gemini-api/terms). Nunca debe recibir datos de un brief real de IH.
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 45.0,
        transport: Transport | None = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "GEMINI_API_KEY", "")
        self.model = model if model is not None else getattr(settings, "GEMINI_MODEL", "")
        self.timeout = timeout
        self.transport = transport or _default_transport

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key or not self.model:
            raise AIProviderError(
                "Gemini requiere GEMINI_API_KEY y GEMINI_MODEL configurados explícitamente."
            )
        request_data = {
            "instruction": request.instruction,
            "authorized_context": request.authorized_context,
            "output_format": request.output_format,
        }
        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "Trabaja únicamente con datos sintéticos o públicos autorizados para "
                            "evaluación. No inventes hechos ni uses información confidencial."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(request_data, ensure_ascii=False)}],
                }
            ],
        }
        headers = {
            "content-type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        try:
            response = self.transport(
                _generate_content_url(self.model), headers, payload, float(self.timeout)
            )
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                "Gemini falló antes de obtener una respuesta válida."
            ) from exc
        content, metadata = _response_text(response)
        return GenerationResponse(
            provider=self.name,
            model=self.model,
            content=content,
            metadata=metadata,
        )
