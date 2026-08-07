"""Pruebas del sistema de tokens de marca (brand/tokens/, brand/product-colors/).

No requieren base de datos: leen directamente los archivos YAML/JSON fuente de brand/.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from branding.services import loader, validators

REPO_ROOT = Path(loader.BRAND_DIR).parent
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@pytest.fixture(autouse=True)
def _clear_brand_cache():
    loader.clear_cache()
    yield
    loader.clear_cache()


def _iter_hex_values(node):
    """Recorre recursivamente un dict/list y produce todos los strings que parecen HEX."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_hex_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_hex_values(value)
    elif isinstance(node, str) and node.startswith("#"):
        yield node


def test_all_documented_colors_have_valid_hex_format():
    colors = loader.load_colors()
    invalid = [v for v in _iter_hex_values(colors) if not HEX_RE.match(v)]
    assert invalid == [], f"Valores HEX con formato inválido en colors.yaml: {invalid}"


def test_all_product_colors_have_valid_hex_format():
    product_colors = loader.load_product_colors()
    invalid = [v for v in _iter_hex_values(product_colors) if not HEX_RE.match(v)]
    assert invalid == [], f"Valores HEX con formato inválido en authorized-colors.yaml: {invalid}"


def test_eight_official_colors_match_authorized_values():
    """Los 8 colores institucionales deben coincidir exactamente con los valores autorizados."""
    expected = {
        "knowledge": "#3B44B5",
        "salmon": "#F06C6A",
        "pink": "#E070A2",
        "technology": "#923472",
        "youth": "#B7DB6E",
        "joy": "#F4CF80",
        "light": "#F4AB63",
        "green": "#28AE62",
    }
    flat = loader.flat_color_map()
    for token, hex_value in expected.items():
        msg = f"Token '{token}' no coincide con el valor autorizado."
        assert flat[token].upper() == hex_value.upper(), msg


def test_all_six_pillars_are_documented():
    pillars = loader.load_product_colors().get("pillars", {})
    expected_pillars = {
        "ingles_general",
        "cambridge",
        "university_programmes",
        "empresas",
        "ielts",
        "spanish_courses",
    }
    assert expected_pillars.issubset(pillars.keys())


def test_every_pillar_has_required_color_fields():
    pillars = loader.load_product_colors().get("pillars", {})
    required_fields = {"primary_hex", "secondary_hex", "background_hex", "cta"}
    for slug, pillar in pillars.items():
        missing = required_fields - pillar.keys()
        assert not missing, f"Pilar '{slug}' no documenta los campos: {missing}"
        assert "background_hex" in pillar["cta"] or "background_hex" in pillar.get("cta", {})


def test_no_duplicate_token_conflicts_between_colors_and_product_colors():
    conflicts = validators.find_duplicate_token_conflicts()
    assert conflicts == [], f"Se encontraron tokens de color contradictorios: {conflicts}"


def test_validate_hex_format():
    assert validators.validate_hex_format("#3B44B5").is_valid
    assert not validators.validate_hex_format("3B44B5").is_valid
    assert not validators.validate_hex_format("#3B44B").is_valid
    assert not validators.validate_hex_format("not-a-color").is_valid


def test_validate_color_is_authorized_accepts_official_palette():
    assert validators.validate_color_is_authorized("#3B44B5").is_valid
    assert validators.validate_color_is_authorized("#E31736").is_valid  # extensión IELTS confirmada


def test_validate_color_is_authorized_rejects_unknown_color():
    result = validators.validate_color_is_authorized("#123456")
    assert not result.is_valid
    assert "paleta institucional" in result.reason


def test_validate_product_color_accepts_documented_pillar_color():
    assert validators.validate_product_color("cambridge", "#923472").is_valid
    assert validators.validate_product_color("ielts", "#E31736").is_valid


def test_validate_product_color_rejects_color_from_another_pillar_context():
    # Un color que no aparece en ningún campo documentado para el pilar debe rechazarse.
    result = validators.validate_product_color("cambridge", "#112233")
    assert not result.is_valid


def test_validate_product_color_rejects_unknown_pillar():
    result = validators.validate_product_color("no-existe", "#3B44B5")
    assert not result.is_valid
    assert "desconocido" in result.reason


def test_rainbow_uses_official_pdf_variant_not_rejected_teal_variant():
    rainbow = loader.load_colors()["rainbow"]
    hex_values = {c.upper() for c in rainbow["colors_hex"]}
    assert "#F4AB63" in hex_values, "Debe incluir Light Orange (versión oficial aprobada)."
    assert "#407B98" not in hex_values, "No debe incluir el 'Teal' rechazado por el cliente."
    assert "rejected_variant" in rainbow


def test_motion_tokens_are_explicitly_marked_as_not_official():
    motion = loader.load_motion()
    assert motion["status"] == "NOT_OFFICIAL_PENDING_BRAND_APPROVAL"


@pytest.mark.parametrize(
    "generated_relpath",
    [
        "brand/tokens/colors.json",
        "brand/generated/ih-brand.css",
        "brand/generated/tokens.js",
        "brand/generated/tailwind-preset.js",
    ],
)
def test_generated_file_exists(generated_relpath):
    msg = f"Falta el archivo generado: {generated_relpath}"
    assert (REPO_ROOT / generated_relpath).exists(), msg


def test_generated_files_are_in_sync_with_yaml_sources():
    """Falla si brand/tokens/colors.json o brand/generated/* quedaron desactualizados
    respecto a los YAML fuente (brand/scripts/generate_tokens.py --check)."""
    script = REPO_ROOT / "brand" / "scripts" / "generate_tokens.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Los archivos generados de brand/ están desactualizados respecto a los YAML fuente.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_colors_json_is_valid_json_and_matches_source():
    import json

    colors_json_path = REPO_ROOT / "brand" / "tokens" / "colors.json"
    data = json.loads(colors_json_path.read_text(encoding="utf-8"))
    colors_yaml = loader.load_colors()
    json_hex = data["primary_palette"]["knowledge"]["hex"]
    yaml_hex = colors_yaml["primary_palette"]["knowledge"]["hex"]
    assert json_hex == yaml_hex
