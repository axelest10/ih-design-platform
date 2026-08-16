import pytest
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from catalog.models import Branch
from designs.models import DesignVersion
from materials.models import MaterialType
from materials.services.catalog import VENUE_KIT_DEFAULT_PRODUCT_SLUGS


@pytest.mark.django_db
def test_venue_kit_exposes_six_confirmed_default_pillars_and_all_formats():
    response = APIClient().get("/api/v1/material-types/")

    assert response.status_code == 200
    venue_kit = next(item for item in response.json() if item["slug"] == "venue-kit")
    assert venue_kit["priority_product_slugs"] == VENUE_KIT_DEFAULT_PRODUCT_SLUGS
    assert [item["template_key"] for item in venue_kit["default_deliverables"]] == [
        "square-v1",
        "story-v1",
        "portrait-v1",
        "brochure-a4-v1",
        "presentation-16x9-v1",
    ]
    assert {item["product_slug"] for item in venue_kit["available_products"]} >= set(
        VENUE_KIT_DEFAULT_PRODUCT_SLUGS
    )


@pytest.mark.django_db
def test_venue_kit_seeds_official_branches_with_provenance():
    assert Branch.objects.count() == 35
    branch = Branch.objects.get(code="pe-san-borja")
    assert branch.country == "PE"
    assert branch.source_url == "https://ihlima.com/sedes/"
    assert branch.official_contact_data["source_status"] == "confirmed"
    assert "cta" in branch.official_contact_data["needs_confirmation"]


@pytest.mark.django_db
def test_venue_kit_defaults_to_six_products_but_accepts_future_catalog_slugs():
    client = APIClient()
    venue_kit = MaterialType.objects.get(slug="venue-kit")
    response = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": venue_kit.pk,
            "name": "Paquete sede Bogotá",
            "country": "CO",
            "branch": Branch.objects.get(code="co-bogota-carrera-18a").pk,
            "brief_context": {"audience": "Público local"},
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["product_slugs"] == VENUE_KIT_DEFAULT_PRODUCT_SLUGS


@pytest.mark.django_db
def test_venue_kit_rejects_unknown_product_slug():
    client = APIClient()
    venue_kit = MaterialType.objects.get(slug="venue-kit")
    response = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": venue_kit.pk,
            "name": "Paquete inválido",
            "country": "MX",
            "product_slugs": ["producto-inventado"],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "product_slugs" in response.json()


@pytest.mark.django_db
def test_venue_kit_generation_reuses_social_document_and_presentation_renderers():
    client = APIClient()
    venue_kit = MaterialType.objects.get(slug="venue-kit")
    bundle = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": venue_kit.pk,
            "name": "Paquete sede Condesa",
            "country": "MX",
            "branch": Branch.objects.get(code="mx-condesa").pk,
            "product_slugs": ["general-english"],
            "brief_context": {
                "brand_logo_key": "ih-mexico-classic-png",
                "headline": "Inglés para cada meta",
                "body": "Aprende con una sede cercana y acompañamiento internacional.",
                "cta": "Conoce la sede",
                "audience": "Personas de la zona",
                "objective": "Presentar los programas de la sede",
            },
        },
        format="json",
    )
    assert bundle.status_code == 201, bundle.json()

    response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/", format="json"
    )

    assert response.status_code == 201, response.json()
    assert len(response.json()["items"]) == 5
    versions = DesignVersion.objects.filter(design__brief__material_type__slug__in=[
        "social-post", "brochure", "presentation"
    ])
    assert {version.template_key for version in versions} >= {
        "square-v1",
        "story-v1",
        "portrait-v1",
        "brochure-a4-v1",
        "presentation-16x9-v1",
    }
    assert DesignBrief.objects.filter(branch__code="mx-condesa").count() == 5
    assert all(
        "venue" in brief.brief_data and brief.brief_data["venue"]["source_status"] == "confirmed"
        for brief in DesignBrief.objects.filter(branch__code="mx-condesa")
    )
