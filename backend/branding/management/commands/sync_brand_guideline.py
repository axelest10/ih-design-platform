"""Sincroniza el BrandGuideline de IH México en base de datos desde brand/ (archivos fuente).

brand/ (YAML) es la fuente de verdad; este comando construye/actualiza el registro de
BrandGuideline correspondiente para que quede disponible vía la API existente
(GET /api/v1/branding/). No inventa datos: toma directamente los valores de
brand/ih-mexico.yaml y brand/tokens/*.yaml.

Uso:
    python manage.py sync_brand_guideline
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from branding.models import BrandGuideline
from branding.services import loader


class Command(BaseCommand):
    help = "Sincroniza BrandGuideline (DB) desde brand/ (archivos YAML fuente de verdad)."

    def handle(self, *args, **options):
        loader.clear_cache()
        brand = loader.load_brand_manifest()
        colors = loader.load_colors()
        typography = loader.load_typography()
        product_colors = loader.load_product_colors()

        palette = {
            "primary_palette": colors.get("primary_palette", {}),
            "secondary_palette": colors.get("secondary_palette", {}),
            "extended_colors": colors.get("extended_colors", {}),
            "rainbow": colors.get("rainbow", {}),
            "product_colors": product_colors.get("pillars", {}),
        }
        typography_payload = {
            "heading": typography.get("typefaces", {}).get("heading", {}),
            "body": typography.get("typefaces", {}).get("body", {}),
            "type_scale": typography.get("type_scale", {}),
        }

        knowledge_hex = colors.get("primary_palette", {}).get("knowledge", {}).get("hex", "#3B44B5")
        brand_status = brand.get("status")
        is_active = brand_status in ("approved-foundation", "approved")

        guideline, created = BrandGuideline.objects.update_or_create(
            slug=brand.get("brand", "international-house-mexico"),
            defaults={
                "name": brand.get("name", "International House México"),
                "primary_color": knowledge_hex,
                "palette": palette,
                "typography": typography_payload,
                "rules": brand.get("rules", {}),
                "is_active": is_active,
            },
        )

        verb = "creado" if created else "actualizado"
        msg = f"BrandGuideline '{guideline.slug}' {verb} desde brand/."
        self.stdout.write(self.style.SUCCESS(msg))
