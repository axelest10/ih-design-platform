from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from campaigns.models import Campaign
from catalog.models import Product
from designs.models import DesignVersion
from materials.models import MaterialBundleItem


def _email_type(client):
    return next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "email-kit"
    )


def _campaign():
    product = Product.objects.create(code="general-english", name="Inglés General")
    return Campaign.objects.create(
        code="email-spring-2026",
        name="Campaña email primavera",
        product=product,
        starts_on=date.today() - timedelta(days=1),
        ends_on=date.today() + timedelta(days=30),
        approved_copy="Conoce una ruta de aprendizaje de inglés alineada a tus objetivos.",
        offer_data={
            "source_status": "confirmed",
            "source_url": "https://example.com/campaign",
            "benefit": "Evaluación de nivel incluida",
            "cta": "Agenda ahora",
        },
        is_active=True,
    )


def _payload(material_type, campaign, **overrides):
    payload = {
        "material_type": material_type["id"],
        "name": "Email primavera",
        "country": "MX",
        "campaign": campaign.pk if campaign else None,
        "brief_context": {
            "brand_logo_key": "ih-mexico-classic-png",
            "subject": "Mejora tu inglés",
            "preheader": "Una ruta clara para tus próximos objetivos.",
            "headline": "Tu siguiente oportunidad empieza aquí",
            "body": "Conoce una ruta de aprendizaje clara y agenda tu siguiente paso.",
            "cta_label": "Agenda ahora",
            "cta_url": "https://example.com/agenda",
            "unsubscribe_url": "https://example.com/unsubscribe",
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_email_kit_exposes_export_only_template_and_catalog():
    client = APIClient()
    email_type = _email_type(client)

    assert email_type["renderer_family"] == "email-html"
    assert email_type["default_deliverables"][0]["template_key"] == "email-base-v1"
    assert email_type["default_deliverables"][0]["scope"] == "per-bundle"
    assert "general-english" in {
        item["product_slug"] for item in email_type["available_products"]
    }


@pytest.mark.django_db
def test_email_kit_requires_campaign():
    client = APIClient()
    response = client.post(
        "/api/v1/material-bundles/",
        _payload(_email_type(client), None),
        format="json",
    )

    assert response.status_code == 400
    assert "campaign" in response.json()


@pytest.mark.django_db
def test_email_kit_generates_html_export_without_sending():
    client = APIClient()
    campaign = _campaign()
    bundle = client.post(
        "/api/v1/material-bundles/",
        _payload(_email_type(client), campaign),
        format="json",
    )
    assert bundle.status_code == 201, bundle.json()

    response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/",
        format="json",
    )

    assert response.status_code == 201, response.json()
    item = response.json()["items"][0]
    version = DesignVersion.objects.get(design_id=item["design"]["id"])
    assert version.render_data["html_path"].endswith(".html")
    assert "<table" in version.render_data["html"]
    assert "<script" not in version.render_data["html"]
    assert version.render_data["html"].count("max-width:640px") == 1
    brief = MaterialBundleItem.objects.get(pk=item["id"]).brief
    assert brief.brief_data["email_kit"]["export_only"] is True
    assert brief.brief_data["email_kit"]["sending"] is False


@pytest.mark.django_db
def test_email_kit_rejects_unsafe_or_missing_required_context():
    client = APIClient()
    campaign = _campaign()
    payload = _payload(_email_type(client), campaign)
    payload["brief_context"]["cta_url"] = "javascript:alert(1)"
    bundle = client.post("/api/v1/material-bundles/", payload, format="json")
    response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/",
        format="json",
    )

    assert response.status_code == 400
    assert MaterialBundleItem.objects.count() == 0
