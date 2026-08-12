"""Anthropic Messages API provider for structured visual design reviews."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from jsonschema import Draft202012Validator

from ai.services.design_review import (
    VisualReviewProviderError,
    VisualReviewRequest,
    VisualReviewResult,
)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
REQUIRED_REVIEW_CHECKS = (
    "logo_usage",
    "authorized_colors",
    "legibility",
    "safe_area",
    "contrast",
    "hierarchy",
    "visible_copy",
    "additional_logos",
)
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["pass", "needs_changes"]},
        "summary": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": list(REQUIRED_REVIEW_CHECKS)},
                    "status": {"type": "string", "enum": ["pass", "needs_changes"]},
                    "finding": {"type": "string"},
                },
                "required": ["name", "status", "finding"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["decision", "summary", "checks"],
    "additionalProperties": False,
}

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
    """Keep visual structure while excluding large embedded binary logo payloads."""
    return re.sub(
        r"data:[^;\"']+;base64,[A-Za-z0-9+/=]+",
        "embedded-logo://omitted",
        str(svg or ""),
    )


def _optional_image_block(render_data: dict[str, Any]) -> dict[str, Any] | None:
    data_uri = str(render_data.get("preview_image_data_uri") or "")
    match = re.fullmatch(
        r"data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=]+)", data_uri
    )
    if not match:
        return None
    try:
        decoded_size = len(base64.b64decode(match.group(2), validate=True))
    except ValueError:
        return None
    if decoded_size > 7_500_000:
        return None
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": match.group(1),
            "data": match.group(2),
        },
    }


def _review_content(request: VisualReviewRequest) -> list[dict[str, Any]]:
    render_data = request.render_data or {}
    evidence = {
        "version_id": request.version_id,
        "design_id": request.design_id,
        "template_key": request.template_key,
        "visible_content": {
            key: render_data.get(key)
            for key in (
                "headline",
                "headline_lines",
                "body",
                "body_lines",
                "cta",
                "eyebrow",
                "product_slug",
                "logo_name",
                "additional_logo_keys",
            )
        },
        "asset_refs": request.asset_refs,
        "deterministic_validation": request.validation_summary,
    }
    content = []
    image_block = _optional_image_block(render_data)
    if image_block:
        content.append(image_block)
    content.append(
        {
            "type": "text",
            "text": (
                "Revisa únicamente esta versión visual. Evalúa los ocho controles requeridos "
                "con la evidencia disponible. No inventes reglas ni conviertas el resultado en "
                "una aprobación humana. Si un defecto visible o una validación determinista "
                "fallida afecta la pieza, usa needs_changes.\n\n"
                f"EVIDENCIA_JSON:\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
                f"SVG_RENDERIZADO:\n{_sanitized_svg(render_data.get('svg', ''))}"
            ),
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
    errors = sorted(Draft202012Validator(REVIEW_SCHEMA).iter_errors(report), key=str)
    if errors:
        raise VisualReviewProviderError("Anthropic devolvió un reporte fuera del contrato.")
    check_names = [check["name"] for check in report["checks"]]
    if len(check_names) != len(REQUIRED_REVIEW_CHECKS) or set(check_names) != set(
        REQUIRED_REVIEW_CHECKS
    ):
        raise VisualReviewProviderError("Anthropic omitió controles obligatorios del reporte.")
    expected_decision = (
        "needs_changes"
        if any(check["status"] == "needs_changes" for check in report["checks"])
        else "pass"
    )
    if report["decision"] != expected_decision:
        raise VisualReviewProviderError("La decisión de Anthropic contradice sus controles.")
    return report, response.get("id")


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
