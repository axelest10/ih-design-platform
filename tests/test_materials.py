import pytest
from rest_framework.test import APIClient


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

    assert response.status_code == 201
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
