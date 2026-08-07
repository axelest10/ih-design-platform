"""Carga de tokens de marca desde brand/ (fuente única de verdad, archivos YAML/JSON).

Este módulo es la única puerta de entrada del backend hacia el sistema de marca basado en
archivos. No debe usarse desde `catalog`, `campaigns`, `briefs`, `designs` ni `assets`
directamente sobre los archivos de `brand/` — cualquier consumo de tokens/colores/tipografía/
activos de marca desde el resto del backend debe pasar por `branding.services`.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

BRAND_DIR: Path = Path(settings.BASE_DIR) / "brand"
TOKENS_DIR = BRAND_DIR / "tokens"
PRODUCT_COLORS_DIR = BRAND_DIR / "product-colors"
ASSETS_DIR = BRAND_DIR / "assets"


class BrandFileMissingError(FileNotFoundError):
    """Se lanza cuando un archivo de marca esperado no existe en brand/."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BrandFileMissingError(f"Archivo de marca no encontrado: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@functools.cache
def load_colors() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "colors.yaml")


@functools.cache
def load_typography() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "typography.yaml")


@functools.cache
def load_spacing() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "spacing.yaml")


@functools.cache
def load_radius() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "radius.yaml")


@functools.cache
def load_shadows() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "shadows.yaml")


@functools.cache
def load_motion() -> dict[str, Any]:
    return _read_yaml(TOKENS_DIR / "motion.yaml")


@functools.cache
def load_product_colors() -> dict[str, Any]:
    return _read_yaml(PRODUCT_COLORS_DIR / "authorized-colors.yaml")


@functools.cache
def load_brand_manifest() -> dict[str, Any]:
    """brand/ih-mexico.yaml — metadatos generales de la marca."""
    return _read_yaml(BRAND_DIR / "ih-mexico.yaml")


@functools.cache
def load_logo_manifest() -> dict[str, Any]:
    return _read_yaml(ASSETS_DIR / "logos" / "manifest.yaml")


@functools.cache
def load_icon_manifest() -> dict[str, Any]:
    return _read_yaml(ASSETS_DIR / "icons" / "manifest.yaml")


@functools.cache
def load_rainbow_manifest() -> dict[str, Any]:
    return _read_yaml(ASSETS_DIR / "rainbows" / "manifest.yaml")


@functools.cache
def load_globe_manifest() -> dict[str, Any]:
    return _read_yaml(ASSETS_DIR / "illustrations" / "globes" / "manifest.yaml")


def flat_color_map() -> dict[str, str]:
    """Mapa {token: hex} con paleta primaria + secundaria + extensiones confirmadas."""
    colors = load_colors()
    flat: dict[str, str] = {}
    for group in ("primary_palette", "secondary_palette"):
        for name, data in colors.get(group, {}).items():
            flat[name] = data["hex"]
    for name, data in colors.get("extended_colors", {}).items():
        flat[name] = data["hex"]
    return flat


def load_all_tokens() -> dict[str, Any]:
    return {
        "brand": load_brand_manifest(),
        "colors": load_colors(),
        "typography": load_typography(),
        "spacing": load_spacing(),
        "radius": load_radius(),
        "shadows": load_shadows(),
        "motion": load_motion(),
        "product_colors": load_product_colors(),
    }


def clear_cache() -> None:
    """Limpia el cache en memoria de todos los loaders (útil en tests)."""
    for fn in (
        load_colors,
        load_typography,
        load_spacing,
        load_radius,
        load_shadows,
        load_motion,
        load_product_colors,
        load_brand_manifest,
        load_logo_manifest,
        load_icon_manifest,
        load_rainbow_manifest,
        load_globe_manifest,
    ):
        cache_clear = getattr(fn, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()
