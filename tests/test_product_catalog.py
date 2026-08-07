"""Pruebas del catálogo de productos por país (brand/knowledge/product-catalog.yaml/.json).

No requieren base de datos: leen directamente los archivos fuente.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from branding.services import loader

REPO_ROOT = Path(loader.BRAND_DIR).parent
KNOWLEDGE_DIR = REPO_ROOT / "brand" / "knowledge"

REQUIRED_FIELDS = {
    "product_slug",
    "canonical_name",
    "aliases",
    "country",
    "countries",
    "brand_scope",
    "pillar",
    "target_audience",
    "language",
    "modality",
    "product_type",
    "typical_formats",
    "authorized_color_reference",
    "associated_logo_keys",
    "allowed_ctas",
    "source",
    "status",
    "needs_confirmation",
}

VALID_STATUSES = {"confirmed", "inferred", "needs_confirmation", "deprecated"}


def _load_catalog() -> dict:
    with (KNOWLEDGE_DIR / "product-catalog.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_logo_names() -> set[str]:
    manifest_path = REPO_ROOT / "brand" / "assets" / "logos" / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    return {entry["name"] for entry in manifest.get("logos", [])}


def _load_pillar_names() -> set[str]:
    colors_path = REPO_ROOT / "brand" / "product-colors" / "authorized-colors.yaml"
    with colors_path.open("r", encoding="utf-8") as fh:
        colors = yaml.safe_load(fh)
    return set(colors.get("pillars", {}).keys())


def test_product_catalog_json_is_in_sync_with_yaml():
    script = REPO_ROOT / "brand" / "scripts" / "generate_product_catalog.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "product-catalog.json está desactualizado respecto a product-catalog.yaml.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_every_product_has_all_required_fields():
    catalog = _load_catalog()
    for product in catalog["products"]:
        missing = REQUIRED_FIELDS - set(product.keys())
        assert not missing, f"{product.get('product_slug')} le faltan campos: {missing}"


def test_product_slugs_are_unique():
    catalog = _load_catalog()
    slugs = [p["product_slug"] for p in catalog["products"]]
    assert len(slugs) == len(set(slugs)), "Hay product_slug duplicados en product-catalog.yaml"


def test_status_values_are_within_allowed_set():
    catalog = _load_catalog()
    for product in catalog["products"]:
        assert product["status"] in VALID_STATUSES, (
            f"{product['product_slug']} tiene status inválido: {product['status']}"
        )
    for deprecated in catalog.get("deprecated", []):
        assert deprecated["status"] == "deprecated"


def test_associated_logo_keys_exist_in_logo_manifest():
    catalog = _load_catalog()
    logo_names = _load_logo_names()
    for product in catalog["products"]:
        for key in product.get("associated_logo_keys") or []:
            assert key in logo_names, (
                f"{product['product_slug']} referencia un logo inexistente: {key}"
            )


def test_pillar_references_exist_in_authorized_colors():
    catalog = _load_catalog()
    pillar_names = _load_pillar_names()
    for product in catalog["products"]:
        pillar = product.get("pillar")
        if pillar is not None:
            assert pillar in pillar_names, (
                f"{product['product_slug']} referencia un pilar inexistente: {pillar}"
            )


def test_countries_referenced_are_declared_in_countries_block():
    catalog = _load_catalog()
    declared = set(catalog["countries"].keys())
    for product in catalog["products"]:
        for country in product.get("countries") or []:
            assert country in declared, (
                f"{product['product_slug']} referencia un país no declarado: {country}"
            )
        if product.get("country") is not None:
            assert product["country"] in declared


def test_deprecated_entries_point_to_a_real_product():
    catalog = _load_catalog()
    slugs = {p["product_slug"] for p in catalog["products"]}
    for deprecated in catalog.get("deprecated", []):
        assert deprecated["superseded_by"] in slugs


def test_needs_confirmation_flag_matches_uncertain_status():
    """Todo producto needs_confirmation=False debe tener status confirmed (nunca al revés)."""
    catalog = _load_catalog()
    for product in catalog["products"]:
        if not product["needs_confirmation"]:
            assert product["status"] == "confirmed", (
                f"{product['product_slug']} declara needs_confirmation=False sin status confirmed"
            )


@pytest.mark.parametrize(
    "question,expected_slug",
    [
        ("mexico", "spanish-courses"),
        ("colombia", "general-english"),
    ],
)
def test_catalog_can_answer_which_products_exist_per_country(question, expected_slug):
    catalog = _load_catalog()
    country_code = {"mexico": "MX", "colombia": "CO"}[question]
    matching = [
        p["product_slug"]
        for p in catalog["products"]
        if country_code in (p.get("countries") or []) or p.get("country") == country_code
    ]
    assert expected_slug in matching


def test_catalog_can_answer_which_products_use_a_pillar():
    catalog = _load_catalog()
    matching = [
        p["product_slug"]
        for p in catalog["products"]
        if p.get("pillar") == "university_programmes"
    ]
    assert "university-programmes" in matching


def test_catalog_can_answer_which_products_use_a_given_logo():
    catalog = _load_catalog()
    matching = [
        p["product_slug"]
        for p in catalog["products"]
        if "ih-santiago-classic" in (p.get("associated_logo_keys") or [])
    ]
    # Ningún producto del pilar institucional vincula logos regionales directamente hoy
    # (associated_logo_keys solo se usa para sub-marcas/partners) — se documenta el
    # comportamiento actual explícitamente en vez de asumir cobertura que no existe.
    assert matching == []
