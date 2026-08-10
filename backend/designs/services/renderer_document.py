"""Renderizador determinista para documentos PDF respaldados por MaterialTemplate."""
from __future__ import annotations

import html
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from branding.services import loader
from materials.models import MaterialTemplate, MaterialType

from .renderer import DEFAULT_LOGO_NAME, RenderValidationError

DOCUMENT_FONT_NAME = "IHOpenSans"


@dataclass(frozen=True)
class RenderedDocument:
    template_key: str
    template_version: str
    data: dict[str, Any]
    asset_refs: list[str]
    validation_summary: dict[str, Any]
    pdf: bytes


def _register_font() -> str:
    if DOCUMENT_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        font_path = (
            loader.ASSETS_DIR
            / "fonts"
            / "open-sans"
            / "OpenSans-VariableFont_wdth,wght.ttf"
        )
        if not font_path.exists():
            raise RenderValidationError(
                "La tipografía Open Sans no existe en los activos de marca."
            )
        pdfmetrics.registerFont(TTFont(DOCUMENT_FONT_NAME, str(font_path)))
    return DOCUMENT_FONT_NAME


def _color_hex(token: str, *, default: str) -> str:
    colors = loader.load_colors()
    value = colors.get("neutrals", {}).get(token, {}).get("hex")
    if value is None:
        value = loader.flat_color_map().get(token)
    if value is None and token != default:
        return _color_hex(default, default=default)
    if value is None:
        raise RenderValidationError(f"Color token '{token}' no está autorizado.")
    return value


def _approved_logo_path(logo_name: str) -> Path:
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
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise RenderValidationError("El brochure piloto requiere un logo PNG o JPG aprobado.")
    if not path.exists():
        raise RenderValidationError(f"El archivo del logo '{logo_name}' no existe en disco.")
    return path


def _required_text(payload: dict[str, Any], field: str, constraints: dict[str, Any]) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise RenderValidationError(f"'{field}' es obligatorio para este documento.")
    maximum = constraints.get(f"max_{field}_chars")
    if maximum is not None and len(value) > int(maximum):
        raise RenderValidationError(f"'{field}' supera el máximo de {maximum} caracteres.")
    return value


def _draw_paragraph(pdf, text: str, style: ParagraphStyle, x: float, y: float, width: float):
    paragraph = Paragraph(html.escape(text), style)
    _, height = paragraph.wrap(width, A4[1])
    paragraph.drawOn(pdf, x, y - height)
    return height


def _build_pdf(*, headline: str, body: str, cta: str, logo_path: Path, accent: str) -> bytes:
    font_name = _register_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    width, height = A4
    margin = 54
    content_width = width - (margin * 2)
    surface = _color_hex("white", default="white")
    dark = _color_hex("dark_navy", default="dark_navy")

    pdf.setTitle(headline)
    pdf.setAuthor("International House LATAM")
    pdf.setFillColor(HexColor(surface))
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(HexColor(accent))
    pdf.rect(0, height - 18, width, 18, stroke=0, fill=1)

    logo = ImageReader(str(logo_path))
    logo_width, logo_height = logo.getSize()
    target_width = 150
    target_height = min(64, target_width * logo_height / logo_width)
    pdf.drawImage(
        logo,
        margin,
        height - 112,
        width=target_width,
        height=target_height,
        preserveAspectRatio=True,
        mask="auto",
    )

    pdf.setFillColor(HexColor(accent))
    pdf.setFont(font_name, 9)
    pdf.drawString(margin, height - 152, "INTERNATIONAL HOUSE · BROCHURE")
    headline_style = ParagraphStyle(
        "BrochureHeadline",
        fontName=font_name,
        fontSize=30,
        leading=36,
        textColor=HexColor(accent),
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "BrochureBody",
        fontName=font_name,
        fontSize=13,
        leading=20,
        textColor=HexColor(dark),
        alignment=TA_LEFT,
    )
    headline_height = _draw_paragraph(
        pdf, headline, headline_style, margin, height - 180, content_width
    )
    body_top = height - 210 - headline_height
    body_height = _draw_paragraph(pdf, body, body_style, margin, body_top, content_width)
    if body_height > 300:
        raise RenderValidationError("'body' no cabe de forma legible en una página A4.")

    button_y = body_top - body_height - 62
    if button_y < 96:
        raise RenderValidationError("El contenido no cabe de forma legible en una página A4.")
    button_width = pdfmetrics.stringWidth(cta, font_name, 12) + 36
    if button_width > content_width:
        raise RenderValidationError("'cta' no cabe de forma legible en el botón del documento.")
    pdf.setFillColor(HexColor(accent))
    pdf.roundRect(margin, button_y, button_width, 42, 10, stroke=0, fill=1)
    pdf.setFillColor(HexColor(surface))
    pdf.setFont(font_name, 12)
    pdf.drawString(margin + 18, button_y + 14, cta)
    pdf.setFillColor(HexColor(dark))
    pdf.setFont(font_name, 8)
    pdf.drawString(margin, 38, "International House LATAM · ihworld.com")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def render_document_preview(
    payload: dict[str, Any], *, material_type: MaterialType
) -> RenderedDocument:
    template_key = str(payload.get("template_key") or "brochure-a4-v1")
    template = (
        MaterialTemplate.objects.filter(
            key=template_key,
            material_type=material_type,
            material_type__renderer_family=MaterialType.RendererFamily.DOCUMENT,
            active=True,
        )
        .select_related("material_type")
        .first()
    )
    if template is None:
        raise RenderValidationError(
            f"Template de documento '{template_key}' no está disponible para este material."
        )
    if "pdf" not in template.output_formats:
        raise RenderValidationError(f"Template '{template_key}' no declara salida PDF.")

    constraints = template.constraints or {}
    values = {
        field: _required_text(payload, field, constraints)
        for field in template.required_fields
    }
    headline = values.get("headline", str(payload.get("headline") or "").strip())
    body = values.get("body", str(payload.get("body") or "").strip())
    cta = values.get("cta", str(payload.get("cta") or "").strip())
    logo_name = str(payload.get("logo_name") or DEFAULT_LOGO_NAME)
    logo_path = _approved_logo_path(logo_name)
    accent_token = str(payload.get("accent_token") or "knowledge")
    accent_hex = _color_hex(accent_token, default="knowledge")
    pdf_bytes = _build_pdf(
        headline=headline,
        body=body,
        cta=cta,
        logo_path=logo_path,
        accent=accent_hex,
    )
    render_data = {
        "template_key": template.key,
        "template_version": template.version,
        "headline": headline,
        "body": body,
        "cta": cta,
        "logo_name": logo_name,
        "accent_token": accent_token,
    }
    validation_summary = {
        "status": "passed",
        "checks": [
            {"name": "template_registered", "status": "passed"},
            {"name": "required_fields", "status": "passed"},
            {"name": "logo_approved", "status": "passed", "asset": logo_name},
            {"name": "brand_color_authorized", "status": "passed", "hex": accent_hex},
            {"name": "pdf_generated", "status": "passed", "signature": "%PDF-"},
        ],
    }
    return RenderedDocument(
        template_key=template.key,
        template_version=template.version,
        data=render_data,
        asset_refs=[logo_name],
        validation_summary=validation_summary,
        pdf=pdf_bytes,
    )
