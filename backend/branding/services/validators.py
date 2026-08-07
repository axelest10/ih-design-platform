"""Validaciones de marca: formato de color, colores autorizados por producto y logos aprobados.

Reglas de negocio implementadas aquí (y solo aquí, para no duplicar reglas de marca en otras
apps del backend):

1. Todo color HEX debe tener formato válido `#RRGGBB`.
2. Un color solo es "autorizado" si aparece en la paleta institucional
   (brand/tokens/colors.yaml) o en la extensión confirmada (rojo IELTS).
3. El color usado para un pilar/producto debe coincidir con alguno de los campos de color
   documentados para ese pilar en brand/product-colors/authorized-colors.yaml.
4. Un logo solo es válido si su archivo está registrado en
   brand/assets/logos/manifest.yaml con `approved: true`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import loader

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    reason: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - conveniencia
        return self.is_valid


def is_valid_hex_format(value: str) -> bool:
    return bool(HEX_COLOR_RE.match(value or ""))


def validate_hex_format(value: str) -> ValidationResult:
    if is_valid_hex_format(value):
        return ValidationResult(True)
    return ValidationResult(False, f"'{value}' no tiene formato HEX válido (#RRGGBB).")


def authorized_color_set() -> set[str]:
    """Todos los HEX autorizados: paleta institucional + extensión IELTS confirmada."""
    return {hex_value.upper() for hex_value in loader.flat_color_map().values()}


def validate_color_is_authorized(hex_value: str) -> ValidationResult:
    fmt = validate_hex_format(hex_value)
    if not fmt:
        return fmt
    if hex_value.upper() in authorized_color_set():
        return ValidationResult(True)
    return ValidationResult(
        False,
        f"'{hex_value}' no está en la paleta institucional autorizada "
        "(brand/tokens/colors.yaml).",
    )


def pillar_authorized_hex_values(pillar_slug: str) -> set[str]:
    pillars = loader.load_product_colors().get("pillars", {})
    pillar = pillars.get(pillar_slug)
    if pillar is None:
        return set()
    values = {pillar["primary_hex"], pillar["secondary_hex"], pillar["background_hex"]}
    cta = pillar.get("cta") or {}
    if cta.get("background_hex"):
        values.add(cta["background_hex"])
    if cta.get("text_hex"):
        values.add(cta["text_hex"])
    return {v.upper() for v in values}


def validate_product_color(pillar_slug: str, hex_value: str) -> ValidationResult:
    fmt = validate_hex_format(hex_value)
    if not fmt:
        return fmt
    pillars = loader.load_product_colors().get("pillars", {})
    if pillar_slug not in pillars:
        known = ", ".join(sorted(pillars))
        msg = f"Pilar '{pillar_slug}' desconocido. Pilares válidos: {known}."
        return ValidationResult(False, msg)
    if hex_value.upper() in pillar_authorized_hex_values(pillar_slug):
        return ValidationResult(True)
    return ValidationResult(
        False,
        f"'{hex_value}' no es un color autorizado para el pilar '{pillar_slug}'. "
        "Ver brand/product-colors/authorized-colors.yaml.",
    )


def validate_logo(logo_name: str) -> ValidationResult:
    """Un logo es válido solo si aparece en el manifest con approved: true."""
    manifest = loader.load_logo_manifest()
    entries = manifest.get("logos") or []
    for entry in entries:
        if entry.get("name") == logo_name:
            if entry.get("approved") is True:
                return ValidationResult(True)
            msg = f"Logo '{logo_name}' está registrado pero no aprobado (approved=false)."
            return ValidationResult(False, msg)
    return ValidationResult(
        False,
        f"Logo '{logo_name}' no está registrado en brand/assets/logos/manifest.yaml — "
        "no puede usarse. Ver brand/assets/logos/README.md.",
    )


def find_duplicate_token_conflicts() -> list[str]:
    """Detecta tokens de color con el mismo nombre pero valores HEX distintos entre
    brand/tokens/colors.yaml y brand/product-colors/authorized-colors.yaml.

    Devuelve una lista de mensajes de conflicto (vacía si no hay contradicciones).
    """
    conflicts: list[str] = []
    flat = loader.flat_color_map()
    pillars = loader.load_product_colors().get("pillars", {})
    for slug, pillar in pillars.items():
        token = pillar.get("primary_token")
        token_source = pillar.get("primary_token_source", "colors")
        if token_source == "extended_colors":
            colors_data = loader.load_colors().get("extended_colors", {})
            expected = colors_data.get(token, {}).get("hex")
        else:
            expected = flat.get(token)
        if expected and expected.upper() != pillar["primary_hex"].upper():
            conflicts.append(
                f"Pilar '{slug}': color principal {pillar['primary_hex']} no coincide con "
                f"el token '{token}' ({expected}) definido en brand/tokens/colors.yaml."
            )
    return conflicts


def missing_asset_files(
    manifest: dict,
    base_dir,
    path_keys: tuple[str, ...] = ("svg_path", "png_path", "file"),
) -> list[str]:
    """Verifica que los archivos referenciados en un manifest de activos existan en disco.

    `manifest` es un dict ya cargado (p. ej. loader.load_icon_manifest()).
    `base_dir` es la carpeta base contra la que se resuelven las rutas relativas del manifest
    (p. ej. loader.ASSETS_DIR / "icons").
    Devuelve la lista de rutas declaradas que no existen en disco.
    """
    missing: list[str] = []
    entries = manifest.get("icons") or manifest.get("variants") or manifest.get("logos") or []
    for entry in entries:
        for key in path_keys:
            rel_path = entry.get(key)
            if not rel_path:
                continue
            if not (base_dir / rel_path).exists():
                missing.append(str(base_dir / rel_path))
    return missing
