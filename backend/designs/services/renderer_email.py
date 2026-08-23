"""Renderizador HTML autocontenido para previews/exportaciones de email."""
from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass
from typing import Any

from branding.services import loader
from materials.models import MaterialTemplate, MaterialType

from .renderer import RenderValidationError


@dataclass(frozen=True)
class RenderedEmail:
    template_key: str
    template_version: str
    data: dict[str, Any]
    asset_refs: list[str]
    validation_summary: dict[str, Any]
    html: str


def _approved_logo_data_uri(logo_name: str) -> tuple[str, str]:
    entry = next(
        (
            item
            for item in loader.load_logo_manifest().get("logos", [])
            if item.get("name") == logo_name
        ),
        None,
    )
    if entry is None or entry.get("approved") is not True:
        raise RenderValidationError(f"Logo '{logo_name}' no está aprobado en el catálogo.")
    path = loader.ASSETS_DIR / "logos" / entry["file"]
    if not path.exists():
        raise RenderValidationError(f"El archivo del logo '{logo_name}' no existe en disco.")
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}", entry.get("label") or "International House"


def _safe_url(value: str, field: str) -> str:
    value = value.strip()
    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        raise RenderValidationError(f"'{field}' debe ser una URL http(s) válida.")
    return value


def _required(payload: dict[str, Any], field: str, maximum: int | None = None) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise RenderValidationError(f"'{field}' es obligatorio para el email.")
    if maximum and len(value) > maximum:
        raise RenderValidationError(f"'{field}' supera el máximo de {maximum} caracteres.")
    return value


def render_email_preview(
    payload: dict[str, Any], *, material_type: MaterialType
) -> RenderedEmail:
    template_key = str(payload.get("template_key") or "email-base-v1")
    template = (
        MaterialTemplate.objects.filter(
            key=template_key,
            material_type=material_type,
            material_type__renderer_family=MaterialType.RendererFamily.EMAIL_HTML,
            active=True,
        )
        .select_related("material_type")
        .first()
    )
    if template is None:
        raise RenderValidationError(f"Template de email '{template_key}' no está disponible.")
    constraints = template.constraints or {}
    subject = _required(payload, "subject", int(constraints.get("max_subject_chars", 150)))
    preheader = _required(payload, "preheader", int(constraints.get("max_preheader_chars", 180)))
    headline = _required(payload, "headline", int(constraints.get("max_headline_chars", 120)))
    body = _required(payload, "body", int(constraints.get("max_body_chars", 1800)))
    cta_label = _required(payload, "cta_label", int(constraints.get("max_cta_label_chars", 80)))
    cta_url = _safe_url(_required(payload, "cta_url"), "cta_url")
    unsubscribe_url = _safe_url(_required(payload, "unsubscribe_url"), "unsubscribe_url")
    logo_name = _required(payload, "logo_name")
    logo_uri, logo_alt = _approved_logo_data_uri(logo_name)
    body_html = "<br>".join(html.escape(line) for line in body.splitlines())
    body_style = "margin:0;padding:0;background:#f5f5f5;color:#1d2633;font-family:Arial,sans-serif;"
    outer_table_style = "width:100%;background:#f5f5f5;"
    inner_table_style = "width:100%;max-width:640px;background:#ffffff;"
    logo_style = "display:block;width:190px;max-width:100%;height:auto;border:0;"
    headline_style = "margin:0;color:#006f6d;font-size:32px;line-height:1.15;font-weight:700;"
    body_copy_style = "padding:12px 32px 24px;font-size:17px;line-height:1.55;"
    cta_style = "display:inline-block;background:#006f6d;color:#ffffff;"
    cta_style += "text-decoration:none;padding:14px 22px;font-size:16px;font-weight:700;"
    footer_style = "padding:18px 32px;border-top:1px solid #dddddd;"
    footer_style += "font-size:12px;line-height:1.5;color:#5f6773;"
    unsubscribe_style = "color:#5f6773;text-decoration:underline;"
    outer_table = (
        '  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="{outer_table_style}">'
    )
    inner_table = (
        '      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="{inner_table_style}">'
    )
    cta_link = (
        f'          <a href="{html.escape(cta_url, quote=True)}" '
        f'style="{cta_style}">{html.escape(cta_label)}</a>'
    )
    unsubscribe_link = (
        f'          <a href="{html.escape(unsubscribe_url, quote=True)}" '
        f'style="{unsubscribe_style}">Cancelar suscripción</a>'
    )
    output = f"""<!doctype html>
<html lang="{html.escape(str(payload.get('language') or 'es'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(subject)}</title>
</head>
<body style="{body_style}">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{html.escape(preheader)}</div>
{outer_table}
    <tr><td align="center" style="padding:24px 12px;">
{inner_table}
        <tr><td style="padding:28px 32px 18px;text-align:left;">
          <img src="{logo_uri}" alt="{html.escape(logo_alt)}" width="190" style="{logo_style}">
        </td></tr>
        <tr><td style="padding:12px 32px 8px;">
          <h1 style="{headline_style}">{html.escape(headline)}</h1>
        </td></tr>
        <tr><td style="{body_copy_style}">{body_html}</td></tr>
        <tr><td style="padding:0 32px 32px;">
{cta_link}
        </td></tr>
        <tr><td style="{footer_style}">
{unsubscribe_link}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    if re.search(r"<\s*(script|iframe|video|object|embed)\b", output, flags=re.IGNORECASE):
        raise RenderValidationError(
            "El email no puede incluir JavaScript, iframes, video ni embeds."
        )
    return RenderedEmail(
        template_key=template.key,
        template_version=template.version,
        data={
            "template_key": template.key,
            "template_version": template.version,
            "subject": subject,
            "preheader": preheader,
            "headline": headline,
            "logo_name": logo_name,
            "cta_url": cta_url,
            "unsubscribe_url": unsubscribe_url,
        },
        asset_refs=[logo_name],
        validation_summary={
            "status": "passed",
            "checks": [
                {"name": "template_registered", "status": "passed"},
                {"name": "email_required_fields", "status": "passed"},
                {"name": "inline_css_and_tables", "status": "passed"},
                {"name": "unsafe_markup_absent", "status": "passed"},
                {"name": "logo_approved", "status": "passed", "asset": logo_name},
            ],
        },
        html=output,
    )
