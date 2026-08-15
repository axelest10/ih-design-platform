from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from campaigns.models import Campaign
from catalog.models import Product
from designs.models import DesignVersion
from materials.models import MaterialBundleItem


def _sales_type(client):
    return next(
        item for item in client.get("/api/v1/material-types/").json() if item["slug"] == "sales-kit"
    )


def _campaign(**overrides):
    product = Product.objects.create(
        code="general-english",
        name="Inglés General",
        is_active=True,
    )
    values = {
        "code": "sales-spring-2026",
        "name": "Campaña primavera",
        "product": product,
        "approved_copy": "Mejora tu inglés con una ruta de aprendizaje clara.",
        "offer_data": {
            "source_status": "confirmed",
            "source_url": "https://example.com/approved-campaign",
            "offer_type": "benefit",
            "benefit": "Evaluación de nivel incluida",
            "audience": "Adultos profesionales",
            "cta": "Agenda ahora",
            "validity_note": "Vigente durante la campaña",
        },
        "is_active": True,
        "starts_on": date.today() - timedelta(days=1),
        "ends_on": date.today() + timedelta(days=30),
    }
    values.update(overrides)
    return Campaign.objects.create(**values)


def _bundle_payload(material_type, campaign, **overrides):
    payload = {
        "material_type": material_type["id"],
        "name": "Paquete comercial primavera",
        "country": "MX",
        "campaign": campaign.pk if campaign else None,
        "brief_context": {"brand_logo_key": "ih-mexico-classic-png"},
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_sales_kit_exposes_all_active_catalog_products_and_five_deliverables():
    client = APIClient()
    sales_type = _sales_type(client)

    assert sales_type["renderer_family"] == "html-svg"
    assert {item["template_key"] for item in sales_type["default_deliverables"]} == {
        "square-v1",
        "story-v1",
        "portrait-v1",
        "brochure-a4-v1",
        "presentation-16x9-v1",
    }
    assert "general-english" in {item["product_slug"] for item in sales_type["available_products"]}


@pytest.mark.django_db
def test_sales_kit_requires_campaign_and_defaults_product_from_campaign():
    client = APIClient()
    sales_type = _sales_type(client)

    missing_campaign = client.post(
        "/api/v1/material-bundles/",
        _bundle_payload(sales_type, None),
        format="json",
    )
    assert missing_campaign.status_code == 400
    assert "campaign" in missing_campaign.json()

    campaign = _campaign()
    response = client.post(
        "/api/v1/material-bundles/",
        _bundle_payload(sales_type, campaign),
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["product_slugs"] == ["general-english"]


@pytest.mark.django_db
def test_sales_kit_rejects_products_that_do_not_match_campaign():
    client = APIClient()
    sales_type = _sales_type(client)
    campaign = _campaign()

    response = client.post(
        "/api/v1/material-bundles/",
        _bundle_payload(sales_type, campaign, product_slugs=["business-english"]),
        format="json",
    )

    assert response.status_code == 400
    assert "product_slugs" in response.json()


@pytest.mark.django_db
def test_sales_kit_generation_creates_social_brochure_and_presentation_pieces():
    client = APIClient()
    sales_type = _sales_type(client)
    campaign = _campaign()
    bundle = client.post(
        "/api/v1/material-bundles/",
        _bundle_payload(sales_type, campaign),
        format="json",
    )
    assert bundle.status_code == 201, bundle.json()

    response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/",
        format="json",
    )

    assert response.status_code == 201, response.json()
    generated = response.json()
    assert generated["status"] == "in_review"
    assert [item["deliverable_key"] for item in generated["items"]] == [
        "general-english-sales-square",
        "general-english-sales-story",
        "general-english-sales-portrait",
        "sales-brochure",
        "sales-presentation",
    ]
    versions = {
        item["deliverable_key"]: DesignVersion.objects.get(
            design_id=item["design"]["id"]
        )
        for item in generated["items"]
    }
    assert versions["general-english-sales-square"].render_data["html"].startswith(
        "<!doctype html>"
    )
    assert versions["sales-brochure"].render_data["pdf_path"].endswith(".pdf")
    assert versions["sales-presentation"].render_data["pptx_path"].endswith(".pptx")
    brief = MaterialBundleItem.objects.get(deliverable_key="sales-brochure").brief
    snapshot = brief.brief_data["sales_kit"]["campaign_snapshot"]
    assert snapshot["code"] == campaign.code
    assert snapshot["offer_data"]["source_status"] == "confirmed"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "campaign_overrides",
    [
        {"is_active": False},
        {"ends_on": date.today() - timedelta(days=1)},
        {"offer_data": {"source_status": "pending"}},
    ],
)
def test_sales_kit_generation_blocks_inactive_expired_or_unconfirmed_campaign(
    campaign_overrides,
):
    client = APIClient()
    sales_type = _sales_type(client)
    campaign = _campaign(**campaign_overrides)
    bundle = client.post(
        "/api/v1/material-bundles/",
        _bundle_payload(sales_type, campaign),
        format="json",
    )
    response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/",
        format="json",
    )

    assert response.status_code == 400
    assert MaterialBundleItem.objects.count() == 0
