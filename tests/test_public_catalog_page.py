import pytest
from rest_framework.test import APIClient


@pytest.mark.corporate_auth
def test_catalog_page_is_public_and_loads_catalog_assets():
    response = APIClient().get("/catalog.html")

    assert response.status_code == 200
    html = response.content.decode()
    assert "scripts/catalog.js" in html
    assert "styles/catalog.css" in html
    assert "Logos aprobados para LATAM" in html
