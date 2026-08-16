"""Validación determinista de zona segura y legibilidad por versión."""
from __future__ import annotations

from typing import Any

from common.observability import operation_event

from .renderer import TEMPLATE_SPECS

SOCIAL_SAFE_ZONE_POLICIES: dict[str, dict[str, float]] = {
    "square": {
        "left_pct": 6.67,
        "right_pct": 6.67,
        "top_pct": 6.67,
        "bottom_pct": 6.67,
    },
    "portrait": {
        "left_pct": 6.67,
        "right_pct": 6.67,
        "top_pct": 5.33,
        "bottom_pct": 5.33,
    },
    "story": {
        "left_pct": 6.67,
        "right_pct": 6.67,
        "top_pct": 3.75,
        "bottom_pct": 3.75,
    },
}


def _contrast_result(validation_summary: dict[str, Any]) -> dict[str, Any]:
    contrast = next(
        (
            check
            for check in validation_summary.get("checks", [])
            if check.get("name") == "contrast"
        ),
        None,
    )
    if contrast is None:
        return {"status": "needs_confirmation", "reason": "contrast_check_not_available"}
    pairs = contrast.get("pairs") or []
    failures = [pair for pair in pairs if float(pair.get("ratio", 0)) < 4.5]
    return {
        "status": "needs_changes" if failures else "passed",
        "minimum_ratio": 4.5,
        "pairs": pairs,
        "failures": failures,
    }


def check_design_version(version) -> dict[str, Any]:
    template_key = version.template_key
    spec = TEMPLATE_SPECS.get(template_key)
    if spec is None or spec.get("format") not in SOCIAL_SAFE_ZONE_POLICIES:
        return {
            "status": "skipped",
            "reason": "format_without_social_safe_zone_policy",
            "template_key": template_key,
        }

    format_name = spec["format"]
    policy = SOCIAL_SAFE_ZONE_POLICIES[format_name]
    width = float(spec["width"])
    height = float(spec["height"])
    bounds = {
        "left": width * policy["left_pct"] / 100,
        "right": width * (1 - policy["right_pct"] / 100),
        "top": height * policy["top_pct"] / 100,
        "bottom": height * (1 - policy["bottom_pct"] / 100),
    }
    renderer_safe_area = next(
        (
            check
            for check in (version.validation_summary or {}).get("checks", [])
            if check.get("name") == "safe_area"
        ),
        None,
    )
    geometry = {
        "status": (
            renderer_safe_area.get("status", "passed")
            if renderer_safe_area
            else "needs_confirmation"
        ),
        "source": "renderer.safe_area",
        "reason": "renderer_enforced_before_design_version",
        "regions": renderer_safe_area.get("regions", []) if renderer_safe_area else [],
    }
    contrast = _contrast_result(version.validation_summary or {})
    status = (
        "needs_changes"
        if geometry["status"] == "needs_changes" or contrast["status"] == "needs_changes"
        else "passed"
    )
    result = {
        "status": status,
        "format": format_name,
        "template_key": template_key,
        "policy_percentages": policy,
        "canvas": {"width": int(width), "height": int(height)},
        "safe_bounds_px": {key: round(value, 2) for key, value in bounds.items()},
        "geometry": geometry,
        "contrast": contrast,
    }
    operation_event(
        "design.safe_zone_checked",
        design_id=version.design_id,
        version_id=version.pk,
        template_key=template_key,
        status=status,
    )
    return result
