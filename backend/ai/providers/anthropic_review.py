"""Anthropic Messages API provider for structured visual design reviews."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from ai.services.design_review import (
    VisualReviewProviderError,
    VisualReviewRequest,
    VisualReviewResult,
)

from .visual_review_contract import (
    REQUIRED_REVIEW_CHECKS,
    REVIEW_SCHEMA,
    anthropic_image_block,
    review_prompt_text,
    sanitized_svg,
    validate_review_report,
)

__all__ = ["REQUIRED_REVIEW_CHECKS", "REVIEW_SCHEMA", "AnthropicVisualReviewProvider"]

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


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
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise VisualReviewProviderError(
            f"Anthropic rechazó la revisión con HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise VisualReviewProviderError(
            "Anthropic no respondió dentro del tiempo permitido."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisualReviewProviderError("Anthropic devolvió una respuesta no válida.") from exc


def _sanitized_svg(svg: str) -> str:
    """Compatibilidad interna para consumidores existentes."""
    return sanitized_svg(svg)


def _optional_image_block(render_data: dict[str, Any]) -> dict[str, Any] | None:
    return anthropic_image_block(render_data)


def _review_content(request: VisualReviewRequest) -> list[dict[str, Any]]:
    render_data = request.render_data or {}
    content = []
    image_block = _optional_image_block(render_data)
    if image_block:
        content.append(image_block)
    content.append(
        {
            "type": "text",
            "text": review_prompt_text(request),
        }
    )
    return content


def _parse_message(response: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    content = response.get("content")
    if not isinstance(content, list):
        raise VisualReviewProviderError("Anthropic no devolvió bloques de contenido.")
    text = next(
        (
            block.get("text")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ),
        None,
    )
    if not isinstance(text, str):
        raise VisualReviewProviderError("Anthropic no devolvió el reporte estructurado.")
    try:
        report = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VisualReviewProviderError("Anthropic devolvió JSON inválido.") from exc
    return validate_review_report(report, provider_label="Anthropic"), response.get("id")


class AnthropicVisualReviewProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        transport: Transport | None = None,
    ):
        self.api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", "")
        self.model = model or getattr(settings, "ANTHROPIC_MODEL", "")
        self.timeout = timeout or getattr(settings, "ANTHROPIC_TIMEOUT_SECONDS", 45.0)
        self.transport = transport or _default_transport

    def review(self, request: VisualReviewRequest) -> VisualReviewResult:
        if not self.api_key or not self.model:
            raise VisualReviewProviderError(
                "La revisión automática requiere ANTHROPIC_API_KEY y ANTHROPIC_MODEL."
            )
        payload = {
            "model": self.model,
            "max_tokens": 1400,
            "system": (
                "Eres un revisor de calidad visual de International House. Usa solo la "
                "evidencia recibida y devuelve exclusivamente el reporte JSON solicitado."
            ),
            "messages": [{"role": "user", "content": _review_content(request)}],
            "output_config": {
                "format": {"type": "json_schema", "schema": REVIEW_SCHEMA}
            },
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        try:
            response = self.transport(
                ANTHROPIC_MESSAGES_URL, headers, payload, float(self.timeout)
            )
        except VisualReviewProviderError:
            raise
        except Exception as exc:
            raise VisualReviewProviderError(
                "La revisión automática falló antes de obtener una respuesta válida."
            ) from exc
        report, response_id = _parse_message(response)
        return VisualReviewResult(
            decision=report["decision"],
            report={
                **report,
                "integration_status": "active",
                "model": self.model,
                "response_id": response_id,
            },
        )
