from pathlib import Path

import pytest
from rest_framework.test import APIClient


@pytest.mark.corporate_auth
def test_templates_gallery_is_public():
    response = APIClient().get("/templates-gallery.html")

    assert response.status_code == 200
    html = response.content.decode()
    assert "scripts/templates-gallery.js" in html
    assert "Tipos de material y plantillas" in html


def test_templates_gallery_uses_friendly_names_and_role_based_social_visibility():
    script = Path("frontend/scripts/templates-gallery.js").read_text(encoding="utf-8")

    assert "Publicación cuadrada" in script
    assert "Presentaciones (PPTX)" in script
    assert 'fetch("/api/v1/me/")' in script
    assert "user?.is_admin" in script
    assert 'user?.roles?.includes("marketing")' in script
    assert '["square-v1", "portrait-v1"]' in script
