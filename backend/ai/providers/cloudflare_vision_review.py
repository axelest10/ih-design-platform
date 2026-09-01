"""Revisión visual opt-in mediante Cloudflare Workers AI."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from ai.services.design_review import (
    VisualReviewProviderError,
    VisualReviewRequest,
    VisualReviewResult,
)

from .cloudflare_provider import CLOUDFLARE_API_BASE_URL, _cloudflare_error
from .visual_review_contract import (
    REVIEW_SCHEMA,
    preview_image_data_uri,
    review_prompt_text,
    validate_review_report,
)

Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def _invalid_response_error(
    message: str, raw_provider_response: Any
) -> VisualReviewProviderError:
    error = VisualReviewProviderError(message)
    error.audit_metadata = {"raw_provider_response": raw_provider_response}
    return error


def _default_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "content-type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS fijo
            raw_response = response.read().decode("utf-8")
            try:
                return json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise _invalid_response_error(
                    "Cloudflare Workers AI devolvió una respuesta no válida.",
                    raw_response,
                ) from exc
    except HTTPError as exc:
        code, message = _cloudflare_error(exc)
        detail = ": ".join(part for part in (code, message) if part)
        suffix = f" ({detail})" if detail else ""
        if exc.code == 429:
            raise VisualReviewProviderError(
                "Cloudflare Workers AI agotó el límite o la capacidad disponible "
                f"con HTTP 429{suffix}."
            ) from exc
        raise VisualReviewProviderError(
            f"Cloudflare Workers AI rechazó la revisión con HTTP {exc.code}{suffix}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise VisualReviewProviderError(
            "Cloudflare Workers AI no respondió dentro del tiempo permitido."
        ) from exc
    except UnicodeDecodeError as exc:
        raise VisualReviewProviderError(
            "Cloudflare Workers AI devolvió una respuesta no válida."
        ) from exc


def _parse_response(response: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    result = response.get("result", response)
    if not isinstance(result, dict):
        raise _invalid_response_error(
            "Cloudflare Workers AI no devolvió un resultado estructurado.", response
        )
    candidate = result.get("response")
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise _invalid_response_error(
                "Cloudflare Workers AI devolvió JSON inválido.", response
            ) from exc
    if not isinstance(candidate, dict):
        raise _invalid_response_error(
            "Cloudflare Workers AI no devolvió el reporte estructurado.", response
        )
    try:
        report = validate_review_report(candidate, provider_label="Cloudflare Workers AI")
    except VisualReviewProviderError as exc:
        exc.audit_metadata = {"raw_provider_response": response}
        raise
    response_id = result.get("id") or response.get("id")
    return report, response_id if isinstance(response_id, str) else None


class CloudflareVisionReviewProvider:
    """Alternativa gratuita no certificada para revisión visual de marca."""

    name = "cloudflare-workers-ai-vision"

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        model: str | None = None,
        timeout: float = 45.0,
        transport: Transport | None = None,
    ):
        self.account_id = (
            account_id
            if account_id is not None
            else getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
        )
        self.api_token = (
            api_token
            if api_token is not None
            else getattr(settings, "CLOUDFLARE_API_TOKEN", "")
        )
        self.model = (
            model
            if model is not None
            else getattr(settings, "CLOUDFLARE_VISION_MODEL", "")
        )
        self.timeout = timeout
        self.transport = transport or _default_transport

    def review(self, request: VisualReviewRequest) -> VisualReviewResult:
        if not self.account_id or not self.api_token or not self.model:
            raise VisualReviewProviderError(
                "La revisión visual con Cloudflare requiere CLOUDFLARE_ACCOUNT_ID, "
                "CLOUDFLARE_API_TOKEN y CLOUDFLARE_VISION_MODEL."
            )
        payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un revisor de calidad visual de International House. Usa solo "
                        "la evidencia recibida y devuelve exclusivamente el reporte JSON "
                        "solicitado."
                    ),
                },
                {"role": "user", "content": review_prompt_text(request)},
            ],
            "max_tokens": 1400,
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": REVIEW_SCHEMA,
            },
        }
        image_data_uri = preview_image_data_uri(request.render_data or {})
        if image_data_uri:
            payload["image"] = image_data_uri

        model_path = quote(self.model, safe="@/")
        url = (
            f"{CLOUDFLARE_API_BASE_URL}/accounts/{quote(self.account_id, safe='')}"
            f"/ai/run/{model_path}"
        )
        headers = {"authorization": f"Bearer {self.api_token}"}
        try:
            response = self.transport(url, headers, payload, float(self.timeout))
        except VisualReviewProviderError:
            raise
        except Exception as exc:
            raise VisualReviewProviderError(
                "La revisión visual con Cloudflare falló antes de obtener una respuesta válida."
            ) from exc
        report, response_id = _parse_response(response)
        return VisualReviewResult(
            decision=report["decision"],
            report={
                **report,
                "integration_status": "active",
                "model": self.model,
                "response_id": response_id,
            },
        )
