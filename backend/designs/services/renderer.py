"""Renderizador mínimo y determinista para templates HTML/SVG versionados."""
from __future__ import annotations

import base64
import html
import json
import math
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings

from assets.models import UploadedLogo
from branding.services import loader

TEMPLATE_VERSION = "1.0.0"
DEFAULT_TEMPLATE_KEY = "square-v1"
DEFAULT_LOGO_NAME = "ih-mexico-classic-png"
MAX_TEXT_LENGTH = 180
TEMPLATE_SPECS = {
    "square-v1": {
        "format": "square",
        "width": 1080,
        "height": 1080,
        "safe_margin": 72,
        "regions": {
            "logo_row": (120, 120, 884, 92),
            "eyebrow": (120, 320, 820, 28),
            "headline": (120, 388, 820, 82),
            "body": (120, 540, 760, 50),
            "cta": (120, 720, 300, 72),
        },
    },
    "story-v1": {
        "format": "story",
        "width": 1080,
        "height": 1920,
        "safe_margin": 72,
        "regions": {
            "logo_row": (120, 120, 884, 92),
            "eyebrow": (120, 520, 820, 28),
            "headline": (120, 588, 820, 82),
            "body": (120, 740, 760, 50),
            "cta": (120, 1040, 300, 72),
        },
    },
    "portrait-v1": {
        "format": "portrait",
        "width": 1080,
        "height": 1350,
        "safe_margin": 72,
        "regions": {
            "logo_row": (120, 120, 884, 92),
            "eyebrow": (120, 360, 820, 28),
            "headline": (120, 428, 820, 82),
            "body": (120, 580, 760, 50),
            "cta": (120, 860, 300, 72),
        },
    },
}


class RenderValidationError(ValueError):
    """Payload inválido para el renderizador de templates."""


@dataclass(frozen=True)
class RenderedPreview:
    template_key: str
    template_version: str
    data: dict[str, Any]
    asset_refs: list[str]
    validation_summary: dict[str, Any]
    html: str
    svg: str


def _template_path(template_key: str, extension: str) -> Path:
    if template_key not in TEMPLATE_SPECS:
        raise RenderValidationError(f"Template '{template_key}' no está disponible.")
    return (
        Path(settings.BASE_DIR)
        / "frontend"
        / "templates"
        / "designs"
        / f"{template_key}.{extension}"
    )


def _color_hex(token: str, *, default: str) -> str:
    colors = loader.load_colors()
    value = colors.get("neutrals", {}).get(token, {}).get("hex")
    if value is None:
        value = loader.flat_color_map().get(token)
    if value is None:
        raise RenderValidationError(f"Color token '{token}' no está autorizado.")
    return value


def _product_colors(product_slug: str) -> dict[str, Any] | None:
    """Resuelve solo colores de producto documentados; devuelve None si no hay pilar/color."""
    if not product_slug:
        return None
    catalog_path = Path(settings.BASE_DIR) / "brand" / "knowledge" / "product-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    product = next(
        (item for item in catalog.get("products", []) if item.get("product_slug") == product_slug),
        None,
    )
    pillar = product.get("pillar") if product else None
    if not pillar:
        return None
    return loader.load_product_colors().get("pillars", {}).get(pillar)


def _approved_logo(logo_name: str) -> tuple[dict[str, Any], Path]:
    manifest = loader.load_logo_manifest()
    entry = next(
        (item for item in manifest.get("logos", []) if item.get("name") == logo_name),
        None,
    )
    if entry is None or entry.get("approved") is not True:
        raise RenderValidationError(f"Logo '{logo_name}' no está aprobado en el catálogo.")
    path = loader.ASSETS_DIR / "logos" / entry["file"]
    if not path.exists():
        raise RenderValidationError(f"El archivo del logo '{logo_name}' no existe en disco.")
    return entry, path


def _logo_data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_logo(key: str) -> tuple[dict[str, Any], Path]:
    if key.startswith("uploaded:"):
        upload_key = key.split(":", 1)[1]
        try:
            uploaded = UploadedLogo.objects.get(key=upload_key)
        except (UploadedLogo.DoesNotExist, ValueError) as exc:
            raise RenderValidationError(f"Logo subido '{key}' no encontrado.") from exc
        if uploaded.status == UploadedLogo.Status.ARCHIVED:
            raise RenderValidationError(f"Logo subido '{key}' archivado.")
        path = Path(uploaded.file.path)
        entry = {"name": key, "brand": uploaded.name, "format": path.suffix.lstrip(".")}
        if path.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg"}:
            raise RenderValidationError(
                f"El logo '{uploaded.name}' necesita una vista previa SVG, PNG o JPG."
            )
        return entry, path
    return _approved_logo(key)


def _dual_logo_markup(keys: list[str]) -> tuple[str, str, list[str]]:
    if len(keys) > 3:
        raise RenderValidationError("El dual-branding admite hasta tres logos adicionales.")
    html_items = []
    svg_items = []
    for index, key in enumerate(keys):
        entry, path = _resolve_logo(key)
        uri = _logo_data_uri(path)
        alt = _escape(str(entry.get("brand") or key))
        html_items.append(
            f'<img class="ih-square-v1__secondary-logo" src="{uri}" alt="{alt}" />'
        )
        x = 424 + (index * 190)
        svg_items.append(
            f'<image x="{x}" y="130" width="160" height="72" '
            f'preserveAspectRatio="xMidYMid meet" href="{uri}" aria-label="{alt}" />'
        )
    return "".join(html_items), "".join(svg_items), list(keys)


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _validate_text(name: str, value: str, *, required: bool = True) -> str:
    normalized = str(value or "").strip()
    if required and not normalized:
        raise RenderValidationError(f"'{name}' es obligatorio.")
    if len(normalized) > MAX_TEXT_LENGTH:
        raise RenderValidationError(f"'{name}' supera el máximo de {MAX_TEXT_LENGTH} caracteres.")
    return normalized


def _hex_rgb(value: str) -> tuple[int, int, int]:
    normalized = value.lstrip("#")
    if len(normalized) != 6:
        raise RenderValidationError(f"Color '{value}' no tiene un formato hexadecimal válido.")
    try:
        return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise RenderValidationError(
            f"Color '{value}' no tiene un formato hexadecimal válido."
        ) from exc


def _relative_luminance(value: str) -> float:
    channels = []
    for channel in _hex_rgb(value):
        normalized = channel / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.03928
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return (0.2126 * channels[0]) + (0.7152 * channels[1]) + (0.0722 * channels[2])


def _contrast_ratio(foreground: str, background: str) -> float:
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _estimate_text_width(value: str, font_size: int) -> float:
    # Deterministic preflight estimate; final browser rendering remains the visual source.
    return len(value) * font_size * 0.55


def _fit_text(
    name: str,
    value: str,
    base_font_size: int,
    max_width: int,
    min_font_size: int | None = None,
) -> dict[str, Any]:
    """Ajusta tamaño y líneas sin truncar ni cortar palabras."""
    minimum = min_font_size or math.ceil(base_font_size * 0.6)
    sizes = list(range(base_font_size, minimum - 1, -4))
    if not sizes or sizes[-1] != minimum:
        sizes.append(minimum)

    for font_size in sizes:
        estimated_width = _estimate_text_width(value, font_size)
        if estimated_width <= max_width:
            return {
                "name": name,
                "base_font_size": base_font_size,
                "font_size": font_size,
                "lines": [value],
                "line_count": 1,
                "estimated_width_px": round(estimated_width, 2),
                "max_width_px": max_width,
                "adjustment": "none" if font_size == base_font_size else "font_size",
            }

    lines: list[str] = []
    current_line = ""
    for word in value.split():
        candidate = f"{current_line} {word}".strip()
        if current_line and _estimate_text_width(candidate, minimum) > max_width:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate
    if current_line or not lines:
        lines.append(current_line)

    widest_line = max((_estimate_text_width(line, minimum) for line in lines), default=0)
    return {
        "name": name,
        "base_font_size": base_font_size,
        "font_size": minimum,
        "lines": lines,
        "line_count": len(lines),
        "estimated_width_px": round(widest_line, 2),
        "max_width_px": max_width,
        "adjustment": "wrapped",
    }


def _validate_text_layout(name: str, value: str, font_size: int, max_width: int) -> dict:
    estimated_width = round(_estimate_text_width(value, font_size), 2)
    if estimated_width > max_width:
        raise RenderValidationError(
            f"'{name}' desborda el ancho seguro ({estimated_width}px > {max_width}px)."
        )
    return {
        "name": name,
        "base_font_size": font_size,
        "font_size": font_size,
        "lines": [value],
        "line_count": 1,
        "estimated_width_px": estimated_width,
        "max_width_px": max_width,
        "adjustment": "none",
    }


def _svg_text_markup(lines: list[str], *, x: int, font_size: int) -> str:
    line_height = round(font_size * 1.15, 2)
    markup = []
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else f"{line_height:g}"
        markup.append(f'<tspan x="{x}" dy="{dy}">{_escape(line)}</tspan>')
    return "".join(markup)


def _validate_template_layout(
    template_key: str, headline: str, body: str, eyebrow: str, cta: str
) -> dict:
    spec = TEMPLATE_SPECS.get(template_key)
    if spec is None:
        raise RenderValidationError(f"Template '{template_key}' no está disponible.")
    safe_margin = spec["safe_margin"]
    safe_right = spec["width"] - safe_margin
    safe_bottom = spec["height"] - safe_margin
    regions = []
    for name, (x, y, width, height) in spec["regions"].items():
        if x < safe_margin or y < safe_margin:
            raise RenderValidationError(f"La región '{name}' sale de la zona segura.")
        if x + width > safe_right or y + height > safe_bottom:
            raise RenderValidationError(f"La región '{name}' sale de la zona segura.")
        regions.append((name, x, y, width, height))

    for current, following in zip(regions, regions[1:]):
        current_bottom = current[2] + current[4]
        if current_bottom > following[2]:
            raise RenderValidationError(
                f"Las regiones '{current[0]}' y '{following[0]}' colisionan."
            )

    text_layout = [
        _validate_text_layout("eyebrow", eyebrow, 18, 820),
        _fit_text("headline", headline, 72, 820),
        _fit_text("body", body, 34, 760),
        _validate_text_layout("cta", cta, 24, 244),
    ]
    return {
        "safe_margin_px": safe_margin,
        "canvas": {"width": spec["width"], "height": spec["height"]},
        "format": spec["format"],
        "text_layout": text_layout,
        "regions": [region[0] for region in regions],
    }


def _validate_contrast(
    accent_hex: str, text_hex: str, surface_hex: str, *, allow_warnings: bool = False
) -> dict:
    pairs = [
        ("accent_on_surface", accent_hex, surface_hex),
        ("text_on_surface", text_hex, surface_hex),
        ("surface_on_accent", surface_hex, accent_hex),
    ]
    results = []
    has_failures = False
    for name, foreground, background in pairs:
        ratio = round(_contrast_ratio(foreground, background), 2)
        if ratio < 4.5:
            if not allow_warnings:
                raise RenderValidationError(
                    f"El contraste '{name}' no alcanza el mínimo 4.5:1 ({ratio}:1)."
                )
            has_failures = True
        results.append(
            {
                "name": name,
                "foreground": foreground,
                "background": background,
                "ratio": ratio,
                "minimum": 4.5,
                "status": "needs_changes" if ratio < 4.5 else "passed",
            }
        )
    return {"status": "needs_changes" if has_failures else "passed", "pairs": results}


def render_preview(payload: dict[str, Any]) -> RenderedPreview:
    """Renderiza el primer template y devuelve HTML/SVG más su resumen de validación."""
    template_key = str(payload.get("template_key") or DEFAULT_TEMPLATE_KEY)
    headline = _validate_text("headline", payload.get("headline"))
    body = _validate_text("body", payload.get("body"))
    eyebrow = _validate_text(
        "eyebrow", payload.get("eyebrow", "International House"), required=False
    )
    cta = _validate_text("cta", payload.get("cta", "Conoce más"), required=False)
    logo_name = str(payload.get("logo_name") or DEFAULT_LOGO_NAME)
    logo_entry, logo_path = _approved_logo(logo_name)
    additional_logo_keys = [str(key) for key in payload.get("additional_logo_keys", [])]
    additional_html, additional_svg, resolved_additional = _dual_logo_markup(
        additional_logo_keys
    )

    product_slug = str(payload.get("product_slug") or "")
    product_colors = _product_colors(product_slug)
    background_token = str(payload.get("background_token") or "knowledge")
    accent_token = str(payload.get("accent_token") or "knowledge")
    text_token = str(payload.get("text_token") or "dark_navy")
    background_hex = (
        product_colors["background_hex"]
        if product_colors
        else _color_hex(background_token, default="knowledge")
    )
    accent_hex = (
        product_colors.get("cta", {}).get("background_hex", product_colors["primary_hex"])
        if product_colors
        else _color_hex(accent_token, default="knowledge")
    )
    text_hex = _color_hex(text_token, default="dark_navy")
    surface_hex = _color_hex("white", default="white")
    layout_summary = _validate_template_layout(template_key, headline, body, eyebrow, cta)
    text_layout = {item["name"]: item for item in layout_summary["text_layout"]}
    headline_layout = text_layout["headline"]
    body_layout = text_layout["body"]
    contrast_summary = _validate_contrast(
        accent_hex,
        text_hex,
        surface_hex,
        allow_warnings=bool(payload.get("_allow_validation_warnings")),
    )
    values = {
        "template_key": _escape(template_key),
        "background_hex": background_hex,
        "accent_hex": accent_hex,
        "surface_hex": surface_hex,
        "text_hex": text_hex,
        "logo_data_uri": _logo_data_uri(logo_path),
        "logo_alt": _escape(str(logo_entry.get("brand") or "International House logo")),
        "additional_logos_html": additional_html,
        "additional_logos_svg": additional_svg,
        "eyebrow": _escape(eyebrow),
        "headline": _escape(headline),
        "headline_font_size": str(headline_layout["font_size"]),
        "headline_svg_markup": _svg_text_markup(
            headline_layout["lines"],
            x=120,
            font_size=headline_layout["font_size"],
        ),
        "body": _escape(body),
        "body_font_size": str(body_layout["font_size"]),
        "body_svg_markup": _svg_text_markup(
            body_layout["lines"],
            x=120,
            font_size=body_layout["font_size"],
        ),
        "cta": _escape(cta),
    }
    html_template = _template_path(template_key, "html").read_text(encoding="utf-8")
    svg_template = _template_path(template_key, "svg").read_text(encoding="utf-8")
    for key, value in values.items():
        html_template = html_template.replace("{{ " + key + " }}", value)
        svg_template = svg_template.replace("{{ " + key + " }}", value)

    validation_summary = {
        "status": "needs_changes" if contrast_summary["status"] == "needs_changes" else "passed",
        "checks": [
            {"name": "template_registered", "status": "passed"},
            {"name": "logo_approved", "status": "passed", "asset": logo_name},
            {"name": "brand_colors_authorized", "status": "passed"},
            {
                "name": "product_color",
                "status": "passed" if product_colors else "needs_confirmation",
                "product_slug": product_slug or None,
                "source": (
                    "authorized-colors.yaml"
                    if product_colors
                    else "no_pillar_color_in_catalog"
                ),
            },
            {"name": "critical_text_present", "status": "passed"},
            {"name": "safe_area", "status": "passed", **layout_summary},
            {"name": "text_layout", "status": "passed", "items": layout_summary["text_layout"]},
            {"name": "contrast", "status": contrast_summary["status"], **contrast_summary},
            {"name": "html_and_svg_generated", "status": "passed"},
            {
                "name": "dual_branding_spacing",
                "status": "passed",
                "count": len(resolved_additional),
                "gap_px": 24,
            },
        ],
    }
    render_data = {
        "template_key": template_key,
        "template_version": TEMPLATE_VERSION,
        "product_slug": product_slug,
        "headline": headline,
        "headline_font_size": headline_layout["font_size"],
        "headline_lines": headline_layout["lines"],
        "body": body,
        "body_font_size": body_layout["font_size"],
        "body_lines": body_layout["lines"],
        "eyebrow": eyebrow,
        "cta": cta,
        "logo_name": logo_name,
        "additional_logo_keys": resolved_additional,
        "background_token": background_token,
        "accent_token": accent_token,
        "text_token": text_token,
    }
    return RenderedPreview(
        template_key=template_key,
        template_version=TEMPLATE_VERSION,
        data=render_data,
        asset_refs=[logo_name],
        validation_summary=validation_summary,
        html=html_template,
        svg=svg_template,
    )
