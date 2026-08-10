import pytest
from rest_framework.test import APIClient


@pytest.mark.corporate_auth
def test_brand_rules_page_and_documentation_are_public():
    client = APIClient()

    page = client.get("/brand-rules.html")
    document = client.get("/brand/documentation/logo-rules.md")

    assert page.status_code == 200
    assert "scripts/brand-rules.js" in page.content.decode()
    assert "marked@18.0.7" in page.content.decode()
    assert document.status_code == 200
    assert b"Reglas de logotipo" in b"".join(document.streaming_content)
