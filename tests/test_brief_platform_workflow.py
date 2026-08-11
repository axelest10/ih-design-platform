import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design

PRIMARY_PRODUCTS = {
    "university-programmes",
    "business-english",
    "general-english",
    "ielts-preparation",
    "spanish-courses",
}


@pytest.mark.django_db
def test_brief_options_expose_only_primary_products_and_country_logos():
    response = APIClient().get("/api/v1/briefs/options/", {"country": "CO"})

    assert response.status_code == 200
    payload = response.json()
    assert {product["product_slug"] for product in payload["products"]} == PRIMARY_PRODUCTS
    assert payload["regional_access"] is False
    assert all(
        logo["scope"] in {"regional", "partner", "sub-brand"}
        and (logo["scope"] != "regional" or logo.get("country") == "CO")
        for logo in payload["logos"]
    )


@pytest.mark.django_db
def test_brief_product_color_and_dual_branding_are_saved_without_design():
    client = APIClient()
    response = client.post(
        "/api/v1/briefs/",
        {
            "title": "IELTS en Bogotá",
            "format": "square",
            "country": "CO",
            "product_slug": "ielts-preparation",
            "brand_logo_key": "ih-bogota-svg",
            "additional_logo_keys": ["ielts-test-centre-pantone-svg"],
            "audience": "Adultos que necesitan certificar su inglés",
            "objective": "Generar registros",
            "requested_message": "Prepárate para tu IELTS",
            "language": "es",
            "channel": "instagram",
            "brief_data": {"cta": "register"},
        },
        format="json",
    )
    assert response.status_code == 201
    brief = DesignBrief.objects.get(pk=response.json()["id"])
    assert response.json()["authorized_color"]["primary_hex"] == "#E31736"
    assert brief.additional_logo_keys == ["ielts-test-centre-pantone-svg"]
    assert not Design.objects.filter(brief=brief).exists()
    # Claude review and human review have independent coverage in
    # test_materials.py and test_design_review.py, respectively.


@pytest.mark.django_db
def test_user_can_upload_a_logo_for_future_briefs():
    response = APIClient().post(
        "/api/v1/uploaded-logos/",
        {
            "file": SimpleUploadedFile(
                "school.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml"
            ),
            "name": "Escuela asociada",
            "country": "CO",
            "logo_type": "school",
            "variant": "color",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_catalog"
