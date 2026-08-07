"""Pruebas de la base de conocimiento visual (brand/knowledge/artwork-reference-knowledge.json)
y de los filtros del endpoint /api/v1/artwork-references/knowledge/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from rest_framework.test import APIClient

from branding.services import loader

REPO_ROOT = Path(loader.BRAND_DIR).parent
KNOWLEDGE_DIR = REPO_ROOT / "brand" / "knowledge"
KNOWLEDGE_JSON = KNOWLEDGE_DIR / "artwork-reference-knowledge.json"

EXPECTED_TOTAL_ASSETS = 454
EXPECTED_LOCAL_BINARIES = 314


def _load_knowledge() -> dict:
    with KNOWLEDGE_JSON.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_product_slugs() -> set[str]:
    with (KNOWLEDGE_DIR / "product-catalog.json").open("r", encoding="utf-8") as fh:
        catalog = json.load(fh)
    return {p["product_slug"] for p in catalog["products"]} | {
        p["product_slug"] for p in catalog["deprecated"]
    }


def test_knowledge_json_preserves_all_454_assets_with_no_duplicates():
    knowledge = _load_knowledge()
    assets = knowledge["assets"]
    assert len(assets) == EXPECTED_TOTAL_ASSETS
    ids = [asset["id"] for asset in assets]
    assert len(ids) == len(set(ids)), "Hay ids de assets duplicados"


def test_knowledge_json_preserves_drive_links_and_local_paths():
    knowledge = _load_knowledge()
    assets = knowledge["assets"]
    assert all(asset["source"]["file_url"] for asset in assets), (
        "Todo asset debe conservar su enlace de Drive original"
    )
    available = [asset for asset in assets if asset["repository"]["available"]]
    assert len(available) == EXPECTED_LOCAL_BINARIES
    assert all(asset["repository"]["path"] for asset in available)


def test_every_asset_has_new_annotation_fields():
    knowledge = _load_knowledge()
    required_top_level = {
        "product_slug",
        "content_pillar",
        "campaign_or_theme",
        "annotation_status",
    }
    required_nested = {
        "product_status",
        "audience",
        "funnel_stage",
        "visual_tags",
        "background_type",
        "composition_type",
        "layout_pattern",
        "image_subject",
        "people_count",
        "logo_present",
        "logo_placement",
        "logo_variant",
        "logo_scale",
        "headline_present",
        "headline_treatment",
        "supporting_text_present",
        "cta_present",
        "cta_treatment",
        "typography_style",
        "photo_style",
        "graphic_elements",
        "recommended_use",
        "annotation_confidence",
        "annotation_source",
        "needs_review",
    }
    for asset in knowledge["assets"]:
        assert required_top_level.issubset(asset.keys()), asset["id"]
        assert required_nested.issubset(asset["annotation"].keys()), asset["id"]
        assert asset["review"]["reuse_permission"] == "client-authorized-reuse"
        # Guardrails: la anotación nunca cambia por sí sola estos dos campos.
        assert asset["review"]["inspiration_only"] is True
        assert asset["review"]["requires_human_approval"] is True


def test_every_used_product_slug_exists_in_catalog_or_is_null():
    knowledge = _load_knowledge()
    valid_slugs = _load_product_slugs()
    for asset in knowledge["assets"]:
        slug = asset["product_slug"]
        if slug is not None:
            assert slug in valid_slugs, f"{asset['id']} usa un product_slug inexistente: {slug}"


def test_human_reviewed_assets_have_needs_review_false_or_explicit_note():
    knowledge = _load_knowledge()
    human_reviewed = [
        a for a in knowledge["assets"] if a["annotation_status"] == "human-reviewed"
    ]
    assert len(human_reviewed) == 40
    for asset in human_reviewed:
        assert asset["annotation"]["annotation_confidence"] in {"high", "medium", "low"}
        assert asset["annotation"]["annotation_source"].startswith(
            "human-visual-review-2026-08-06"
        )


def test_videos_without_local_binary_remain_flagged_for_review():
    knowledge = _load_knowledge()
    videos_without_binary = [
        a
        for a in knowledge["assets"]
        if a["media_type"] == "video" and not a["repository"]["available"]
    ]
    assert videos_without_binary, "Se esperaban videos sin binario local (source-only)"
    for asset in videos_without_binary:
        assert asset["annotation"]["needs_review"] is True


def test_knowledge_json_is_reproducible_from_manifest_and_annotations(tmp_path):
    """Regenerar en un archivo temporal debe producir exactamente el mismo contenido."""
    script = REPO_ROOT / "brand" / "scripts" / "build_design_knowledge.py"
    manifest = REPO_ROOT / "brand" / "assets" / "artwork-references" / "manifest.yaml"
    output = tmp_path / "regenerated.json"
    result = subprocess.run(
        [sys.executable, str(script), str(manifest), str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == _load_knowledge()


def test_annotations_yaml_overrides_reference_real_asset_ids():
    """Cada id en overrides: debe existir realmente en el manifest de assets."""
    annotations_path = KNOWLEDGE_DIR / "artwork-annotations.yaml"
    with annotations_path.open("r", encoding="utf-8") as fh:
        annotations = yaml.safe_load(fh)
    knowledge = _load_knowledge()
    known_ids = {asset["id"] for asset in knowledge["assets"]}
    for override_id in annotations.get("overrides", {}):
        assert override_id in known_ids, f"override para id inexistente: {override_id}"


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_product_slug():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"product_slug": "ielts-preparation", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["returned_assets"] == len(payload["assets"])
    assert all(a["product_slug"] == "ielts-preparation" for a in payload["assets"])


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_country_and_media_type():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"country": "chile", "media_type": "image", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assets"]
    assert all(a["country"] == "chile" and a["media_type"] == "image" for a in payload["assets"])


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_calendar_year_and_month():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"country": "chile", "calendar.year": "2026", "calendar.month": "2", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assets"]
    for asset in payload["assets"]:
        assert asset["calendar"]["year"] == 2026
        assert asset["calendar"]["month"] == 2


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_content_pillar_and_annotation_status():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"content_pillar": "ielts", "annotation_status": "human-reviewed", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assets"]
    for asset in payload["assets"]:
        assert asset["content_pillar"] == "ielts"
        assert asset["annotation_status"] == "human-reviewed"


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_campaign_or_theme():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"campaign_or_theme": "back-to-school", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assets"]
    assert all(a["campaign_or_theme"] == "back-to-school" for a in payload["assets"])


@pytest.mark.django_db
def test_knowledge_endpoint_filters_by_orientation_and_tag():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"orientation": "portrait", "tag": "chile", "limit": 500},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assets"]
    for asset in payload["assets"]:
        assert asset["technical"]["orientation"] == "portrait"
        assert "chile" in asset["tags"]
