from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from materials.models import MaterialTemplate


def _role_client(role):
    user = get_user_model().objects.create_user(
        username=f"quick-{role}",
        email=f"quick-{role}@ihmexico.com",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_designer_can_create_persisted_quick_design():
    client, user = _role_client("designer")

    response = client.post(
        "/api/v1/materials/quick-design/",
        {
            "template_key": "square-v1",
            "country": "MX",
            "product_slug": "general-english",
            "brand_logo_key": "ih-mexico-classic-png",
            "additional_logo_keys": [],
            "headline": "Inglés para ti",
            "body": "Aprende cerca de ti.",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    payload = response.json()
    assert payload["preview"]["html"].startswith("<!doctype html>")
    assert payload["preview"]["svg"].startswith("<svg")
    design = Design.objects.get(pk=payload["design_id"])
    assert design.brief.created_by == user
    assert design.brief.material_type.slug == "social-post"
    assert design.brief.brief_data["source"] == "quick-design"
    version = DesignVersion.objects.get(design=design)
    assert version.template_key == "square-v1"
    assert version.render_data["headline"] == "Inglés para ti"
    assert DesignBrief.objects.filter(pk=payload["brief_id"]).exists()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_viewer_cannot_create_quick_design():
    client, _ = _role_client("viewer")

    response = client.post(
        "/api/v1/materials/quick-design/",
        {"template_key": "square-v1"},
        format="json",
    )

    assert response.status_code == 403
    assert not Design.objects.exists()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_quick_design_rejects_missing_template_fields_without_persistence():
    client, _ = _role_client("marketing")

    response = client.post(
        "/api/v1/materials/quick-design/",
        {
            "template_key": "square-v1",
            "country": "MX",
            "product_slug": "general-english",
            "brand_logo_key": "ih-mexico-classic-png",
            "headline": "Falta el cuerpo",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "body" in response.json()["detail"]
    assert not Design.objects.exists()


@pytest.mark.django_db
def test_material_templates_expose_friendly_field_labels():
    template = MaterialTemplate.objects.get(key="brochure-a4-v1")

    assert template.field_labels == {
        "headline": "Título principal",
        "body": "Texto del cuerpo",
        "cta": "Llamada a la acción",
    }
    response = APIClient().get("/api/v1/material-templates/")
    serialized = next(item for item in response.json() if item["key"] == template.key)
    assert serialized["field_labels"] == template.field_labels


def test_templates_page_contains_quick_editor_and_persistence_endpoint():
    html = Path("frontend/templates-gallery.html").read_text(encoding="utf-8")
    script = Path("frontend/scripts/templates-gallery.js").read_text(encoding="utf-8")

    assert 'id="quick-design-dialog"' in html
    assert "Usar esta plantilla" in script
    assert "/api/v1/materials/quick-design/" in script
    assert "can_create_briefs" in script
