import pytest
from rest_framework.test import APIClient


@pytest.mark.corporate_auth
def test_templates_gallery_is_public():
    response = APIClient().get("/templates-gallery.html")

    assert response.status_code == 200
    html = response.content.decode()
    assert "scripts/templates-gallery.js" in html
    assert "Tipos de material y plantillas" in html
