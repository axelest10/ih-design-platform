"""Pruebas de consumo del sistema de marca desde la API del backend."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from branding.models import BrandGuideline
from branding.services import loader


@pytest.fixture(autouse=True)
def _clear_brand_cache():
    loader.clear_cache()
    yield
    loader.clear_cache()


@pytest.mark.django_db
def test_brand_tokens_endpoint_returns_full_token_set():
    response = APIClient().get("/api/v1/branding/tokens/")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "brand",
        "colors",
        "typography",
        "spacing",
        "radius",
        "shadows",
        "motion",
        "product_colors",
    }
    assert payload["colors"]["primary_palette"]["knowledge"]["hex"] == "#3B44B5"
    assert "cambridge" in payload["product_colors"]["pillars"]


@pytest.mark.django_db
def test_brand_logos_endpoint_returns_latam_catalog():
    response = APIClient().get("/api/v1/branding/logos/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "2.0.0"
    # Conteo literal del manifest actual; debe actualizarse cuando se incorporen más logos.
    assert payload["count"] == 90
    assert len(payload["logos"]) == 90
    assert {entry["scope"] for entry in payload["logos"]} >= {
        "regional",
        "global",
        "sub-brand",
        "partner",
    }


@pytest.mark.django_db
def test_brand_logos_endpoint_filters_by_country_and_scope():
    response = APIClient().get(
        "/api/v1/branding/logos/",
        {"country": "CO", "scope": "regional"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"] == {"country": "CO", "scope": "regional"}
    assert payload["count"] == 10
    assert {entry["country"] for entry in payload["logos"]} == {"CO"}
    assert {entry["scope"] for entry in payload["logos"]} == {"regional"}


@pytest.mark.django_db
def test_validate_color_endpoint_accepts_official_color():
    response = APIClient().get("/api/v1/branding/validate-color/", {"hex": "#3B44B5"})

    assert response.status_code == 200
    assert response.json()["is_valid"] is True


@pytest.mark.django_db
def test_validate_color_endpoint_rejects_unknown_color():
    response = APIClient().get("/api/v1/branding/validate-color/", {"hex": "#123456"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["reason"]


@pytest.mark.django_db
def test_validate_color_endpoint_checks_pillar_when_provided():
    client = APIClient()
    url = "/api/v1/branding/validate-color/"
    ok = client.get(url, {"hex": "#923472", "pillar": "cambridge"})
    # #B7DB6E (Youth Green) es el color principal de Inglés General, no forma parte de
    # ningún campo documentado para el pilar Cambridge.
    bad = client.get(url, {"hex": "#B7DB6E", "pillar": "cambridge"})

    assert ok.json()["is_valid"] is True
    assert bad.json()["is_valid"] is False


@pytest.mark.django_db
def test_sync_brand_guideline_command_upserts_brand_guideline():
    from django.core.management import call_command

    assert not BrandGuideline.objects.filter(slug="international-house-mexico").exists()

    call_command("sync_brand_guideline")

    guideline = BrandGuideline.objects.get(slug="international-house-mexico")
    assert guideline.name == "International House México"
    assert guideline.primary_color == "#3B44B5"
    assert "primary_palette" in guideline.palette
    assert guideline.is_active is True


@pytest.mark.django_db
def test_branding_guideline_api_serves_synced_data():
    from django.core.management import call_command

    call_command("sync_brand_guideline")

    response = APIClient().get("/api/v1/branding/")

    assert response.status_code == 200
    payload = response.json()
    items = payload.get("results", []) if isinstance(payload, dict) else payload
    slugs = {item["slug"] for item in items}
    assert "international-house-mexico" in slugs
