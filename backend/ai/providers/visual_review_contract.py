"""Contrato y evidencia compartidos por los revisores visuales automáticos."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from jsonschema import Draft202012Validator

from ai.services.design_review import VisualReviewProviderError, VisualReviewRequest

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


def sanitized_svg(svg: str) -> str:
    """Conserva la estructura visual sin incluir binarios embebidos extensos."""
    return re.sub(
        r"data:[^;\"']+;base64,[A-Za-z0-9+/=]+",
        "embedded-logo://omitted",
        str(svg or ""),
    )


def preview_image_data_uri(render_data: dict[str, Any]) -> str | None:
    """Devuelve una vista previa base64 validada y acotada, si está disponible."""
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
    return data_uri


def anthropic_image_block(render_data: dict[str, Any]) -> dict[str, Any] | None:
    """Convierte la vista previa validada al bloque de imagen de Anthropic."""
    data_uri = preview_image_data_uri(render_data)
    if not data_uri:
        return None
    match = re.fullmatch(
        r"data:(image/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/=]+)", data_uri
    )
    if not match:  # pragma: no cover - protegido por preview_image_data_uri
        return None
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": match.group(1),
            "data": match.group(2),
        },
    }


def review_prompt_text(request: VisualReviewRequest) -> str:
    """Construye la evidencia común sin reglas inventadas ni secretos binarios."""
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
    return (
        "Revisa únicamente esta versión visual. Evalúa los ocho controles requeridos "
        "con la evidencia disponible. No inventes reglas ni conviertas el resultado en "
        "una aprobación humana. Si un defecto visible o una validación determinista "
        "fallida afecta la pieza, usa needs_changes.\n\n"
        f"EVIDENCIA_JSON:\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
        f"SVG_RENDERIZADO:\n{sanitized_svg(render_data.get('svg', ''))}"
    )


def validate_review_report(report: Any, *, provider_label: str) -> dict[str, Any]:
    """Valida schema, presencia de controles y coherencia de la decisión."""
    errors = sorted(Draft202012Validator(REVIEW_SCHEMA).iter_errors(report), key=str)
    if errors:
        raise VisualReviewProviderError(
            f"{provider_label} devolvió un reporte fuera del contrato."
        )
    check_names = [check["name"] for check in report["checks"]]
    if len(check_names) != len(REQUIRED_REVIEW_CHECKS) or set(check_names) != set(
        REQUIRED_REVIEW_CHECKS
    ):
        raise VisualReviewProviderError(
            f"{provider_label} omitió controles obligatorios del reporte."
        )
    expected_decision = (
        "needs_changes"
        if any(check["status"] == "needs_changes" for check in report["checks"])
        else "pass"
    )
    if report["decision"] != expected_decision:
        raise VisualReviewProviderError(
            f"La decisión de {provider_label} contradice sus controles."
        )
    return report
