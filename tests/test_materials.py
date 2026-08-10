import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from ai.services import VisualReviewResult, run_automatic_design_review
from designs.models import Design, DesignVersion
from materials.models import MaterialType


@pytest.mark.django_db
def test_social_post_type_reuses_registered_render_templates():
    client = APIClient()
    material_types = client.get("/api/v1/material-types/")

    assert material_types.status_code == 200
    social_post = next(
        item for item in material_types.json() if item["slug"] == "social-post"
    )
    assert social_post["renderer_family"] == "html-svg"
    assert social_post["channel"] == "instagram"
    assert social_post["supported_formats"] == ["square", "story", "portrait"]

    templates = client.get("/api/v1/material-templates/")
    assert templates.status_code == 200
    social_templates = {
        item["key"]: item
        for item in templates.json()
        if item["material_type"] == social_post["id"]
    }
    assert {
        key: template["dimensions"] for key, template in social_templates.items()
    } == {
        "square-v1": [1080, 1080],
        "story-v1": [1080, 1920],
        "portrait-v1": [1080, 1350],
    }
    assert all(
        template["output_formats"] == ["html", "svg"]
        for template in social_templates.values()
    )


def _role_client(role):
    user = get_user_model().objects.create_user(
        username=f"{role}@ihmexico.com",
        email=f"{role}@ihmexico.com",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_designer_can_read_but_cannot_mutate_material_catalog():
    client = _role_client("designer")
    material_type = MaterialType.objects.get(slug="social-post")

    assert client.get("/api/v1/material-types/").status_code == 200
    assert client.get("/api/v1/material-templates/").status_code == 200
    assert client.post(
        "/api/v1/material-types/",
        {
            "slug": "forbidden-type",
            "name": "No permitido",
            "renderer_family": "html-svg",
            "channel": "test",
        },
        format="json",
    ).status_code == 403
    assert client.patch(
        f"/api/v1/material-types/{material_type.pk}/",
        {"name": "No permitido"},
        format="json",
    ).status_code == 403
    assert client.delete(f"/api/v1/material-types/{material_type.pk}/").status_code == 403
    template = material_type.templates.first()
    assert client.post(
        "/api/v1/material-templates/",
        {"material_type": material_type.pk, "key": "forbidden-v1"},
        format="json",
    ).status_code == 403
    assert client.patch(
        f"/api/v1/material-templates/{template.pk}/",
        {"active": False},
        format="json",
    ).status_code == 403
    assert client.delete(f"/api/v1/material-templates/{template.pk}/").status_code == 403


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_platform_admin_can_create_edit_and_delete_material_catalog():
    client = _role_client("platform_admin")
    created_type = client.post(
        "/api/v1/material-types/",
        {
            "slug": "admin-test-type",
            "name": "Tipo administrativo",
            "renderer_family": "html-svg",
            "channel": "internal",
            "supported_formats": ["square"],
        },
        format="json",
    )
    assert created_type.status_code == 201, created_type.json()
    type_id = created_type.json()["id"]
    updated_type = client.patch(
        f"/api/v1/material-types/{type_id}/",
        {"name": "Tipo actualizado"},
        format="json",
    )
    assert updated_type.status_code == 200
    assert updated_type.json()["name"] == "Tipo actualizado"

    created_template = client.post(
        "/api/v1/material-templates/",
        {
            "material_type": type_id,
            "key": "admin-test-v1",
            "dimensions": [1080, 1080],
            "output_formats": ["html", "svg"],
            "required_fields": ["headline"],
        },
        format="json",
    )
    assert created_template.status_code == 201, created_template.json()
    template_id = created_template.json()["id"]
    updated_template = client.patch(
        f"/api/v1/material-templates/{template_id}/",
        {"active": False},
        format="json",
    )
    assert updated_template.status_code == 200
    assert updated_template.json()["active"] is False
    assert client.delete(f"/api/v1/material-templates/{template_id}/").status_code == 204
    assert client.delete(f"/api/v1/material-types/{type_id}/").status_code == 204


@pytest.mark.django_db
def test_school_kit_exposes_all_active_products_with_two_priorities_first():
    response = APIClient().get("/api/v1/material-types/", {"country": "MX"})

    assert response.status_code == 200
    school_kit = next(item for item in response.json() if item["slug"] == "school-kit")
    products = school_kit["available_products"]
    assert products[0]["product_slug"] == "qc-2026"
    assert products[1]["product_slug"] == "teacher-training-certifications"
    assert all("product_slug" in product for product in products)
    assert all(product["product_slug"] != "live-english" for product in products)


@pytest.mark.django_db
def test_school_kit_bundle_accepts_catalog_products_and_reports_priorities():
    client = APIClient()
    material_types = client.get("/api/v1/material-types/").json()
    school_kit = next(item for item in material_types if item["slug"] == "school-kit")

    response = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": school_kit["id"],
            "name": "Paquetería piloto para colegio",
            "country": "MX",
            "product_slugs": ["general-english", "qc-2026", "teacher-training-certifications"],
            "brief_context": {"audience": "Colegios con convenio institucional"},
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["priority_products"] == [
        "qc-2026",
        "teacher-training-certifications",
    ]


@pytest.mark.django_db
def test_school_kit_bundle_rejects_deprecated_product_slug():
    client = APIClient()
    material_type = next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "school-kit"
    )

    response = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": material_type["id"],
            "name": "Paquetería inválida",
            "product_slugs": ["live-english"],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "product_slugs" in response.json()


@pytest.mark.django_db
def test_school_kit_type_exposes_three_default_deliverables():
    response = APIClient().get("/api/v1/material-types/", {"country": "MX"})

    school_kit = next(item for item in response.json() if item["slug"] == "school-kit")
    assert [item["template_key"] for item in school_kit["default_deliverables"]] == [
        "square-v1",
        "story-v1",
        "portrait-v1",
    ]


@pytest.mark.django_db
def test_school_kit_generation_creates_three_rendered_pieces_per_product():
    client = APIClient()
    material_type = next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "school-kit"
    )
    payload = {
        "material_type": material_type["id"],
        "name": "Paquetería colegios MX",
        "country": "MX",
        "product_slugs": ["general-english"],
        "brief_context": {
            "brand_logo_key": "ih-mexico-classic-png",
            "headline": "Aprende inglés",
            "body": "Fortalece la comunicación.",
            "cta": "Conoce más",
            "audience": "Colegios con convenio institucional",
            "objective": "Presentar la propuesta educativa",
        },
    }
    bundle_response = client.post("/api/v1/material-bundles/", payload, format="json")
    assert bundle_response.status_code == 201

    response = client.post(
        f"/api/v1/material-bundles/{bundle_response.json()['id']}/generate/",
        format="json",
    )

    assert response.status_code == 201, response.json()
    generated = response.json()
    assert generated["status"] == "in_review"
    assert len(generated["items"]) == 3
    assert {item["design"]["status"] for item in generated["items"]} == {"self_review"}
    assert {item["design"]["claude_review_status"] for item in generated["items"]} == {"pending"}
    assert {
        item["design"]["claude_review"]["integration_status"]
        for item in generated["items"]
    } == {"needs_confirmation"}
    assert {
        item["design"]["claude_review"]["provider"] for item in generated["items"]
    } == {"claude-stub"}
    assert all(item["design"]["claude_review"]["automated"] for item in generated["items"])
    version = DesignVersion.objects.get(design_id=generated["items"][0]["design"]["id"])
    assert version.render_data["product_slug"] == "general-english"
    assert version.render_data["html"].startswith("<!doctype html>")
    assert version.render_data["svg"].startswith("<svg")
    assert version.validation_summary["status"] == "needs_changes"


@pytest.mark.django_db
def test_school_kit_generation_flags_product_without_confirmed_color():
    client = APIClient()
    material_type = next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "school-kit"
    )
    response = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": material_type["id"],
            "name": "Paquetería QC",
            "country": "MX",
            "product_slugs": ["qc-2026"],
            "brief_context": {
                "brand_logo_key": "ih-mexico-classic-png",
                "headline": "Quality Circle",
                "body": "Programa para colegios.",
                "cta": "Más información",
                "audience": "Colegios",
                "objective": "Presentar Quality Circle",
            },
        },
        format="json",
    )
    generated = client.post(
        f"/api/v1/material-bundles/{response.json()['id']}/generate/",
        format="json",
    )

    assert generated.status_code == 201, generated.json()
    version = DesignVersion.objects.get(design_id=generated.json()["items"][0]["design"]["id"])
    assert version.render_data["product_color_status"] == "needs_confirmation"
    product_color_check = next(
        check for check in version.validation_summary["checks"] if check["name"] == "product_color"
    )
    assert product_color_check["status"] == "needs_confirmation"


@pytest.mark.django_db
def test_school_kit_piece_uses_existing_claude_review_status():
    client = APIClient()
    material_type = next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "school-kit"
    )
    bundle = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": material_type["id"],
            "name": "Paquetería revisión",
            "country": "MX",
            "product_slugs": ["general-english"],
            "brief_context": {
                "brand_logo_key": "ih-mexico-classic-png",
                "headline": "Titular de prueba",
                "body": "Mensaje de prueba para la revisión.",
                "cta": "Conoce más",
                "audience": "Colegios",
                "objective": "Probar revisión",
            },
        },
        format="json",
    )
    generated_response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/", format="json"
    )
    assert generated_response.status_code == 201, generated_response.json()
    generated = generated_response.json()
    design_id = generated["items"][0]["design"]["id"]

    review = client.post(
        f"/api/v1/designs/{design_id}/claude-review/",
        {"decision": "pass", "report": {"summary": "La pieza cumple."}},
        format="json",
    )

    assert review.status_code == 200
    assert review.json()["claude_review_status"] == "pass"
    assert review.json()["status"] == "test_ready"
    version = DesignVersion.objects.get(design_id=design_id)
    assert version.claude_review["provider"] == "claude-manual"
    assert version.claude_review["automated"] is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("decision", "expected_design_status"),
    [
        ("pass", Design.Status.TEST_READY),
        ("needs_changes", Design.Status.REVISION_REQUESTED),
    ],
)
def test_automatic_review_provider_reuses_design_version_status(
    decision, expected_design_status
):
    client = APIClient()
    material_type = next(
        item
        for item in client.get("/api/v1/material-types/").json()
        if item["slug"] == "school-kit"
    )
    bundle = client.post(
        "/api/v1/material-bundles/",
        {
            "material_type": material_type["id"],
            "name": "Paquetería revisión automática",
            "country": "MX",
            "product_slugs": ["general-english"],
            "brief_context": {
                "brand_logo_key": "ih-mexico-classic-png",
                "headline": "Titular automático",
                "body": "Mensaje de prueba.",
                "cta": "Conoce más",
                "audience": "Colegios",
                "objective": "Probar revisión automática",
            },
        },
        format="json",
    )
    generated_response = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/", format="json"
    )
    assert generated_response.status_code == 201, generated_response.json()
    generated = generated_response.json()
    version = DesignVersion.objects.get(
        design_id=generated["items"][0]["design"]["id"]
    )

    class TestProvider:
        name = "test-claude"

        def review(self, request):
            assert request.render_data["html"].startswith("<!doctype html>")
            assert request.render_data["svg"].startswith("<svg")
            return VisualReviewResult(
                decision=decision,
                report={"summary": "Resultado controlado de prueba."},
            )

    run_automatic_design_review(version, provider=TestProvider())

    version.refresh_from_db()
    version.design.refresh_from_db()
    assert version.claude_review_status == decision
    assert version.claude_review["provider"] == "test-claude"
    assert version.claude_review["automated"] is True
    assert version.design.status == expected_design_status
