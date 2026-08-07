import pytest
from rest_framework.test import APIClient

from designs.models import DesignVersion


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
    material_type = client.get("/api/v1/material-types/").json()[0]

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
    generated = client.post(
        f"/api/v1/material-bundles/{bundle.json()['id']}/generate/", format="json"
    ).json()
    design_id = generated["items"][0]["design"]["id"]

    review = client.post(
        f"/api/v1/designs/{design_id}/claude-review/",
        {"decision": "pass", "report": {"summary": "La pieza cumple."}},
        format="json",
    )

    assert review.status_code == 200
    assert review.json()["claude_review_status"] == "pass"
    assert review.json()["status"] == "test_ready"
