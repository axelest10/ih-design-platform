import re

import pytest


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path, marker",
    [
        ("/", "Design Platform"),
        ("/index.html", "Design Platform"),
        ("/panel.html", "brief-form"),
    ],
)
def test_frontend_pages_are_served(client, path, marker):
    response = client.get(path)

    assert response.status_code == 200
    assert marker.encode() in response.content


@pytest.mark.django_db
def test_admin_page_is_served(client):
    response = client.get("/admin.html")

    assert response.status_code == 200
    assert b"Panel administrador" in response.content


@pytest.mark.django_db
def test_frontend_html_revalidates_and_references_content_versioned_assets(client):
    response = client.get("/panel.html")
    html = response.content.decode()

    assert set(response["Cache-Control"].split(", ")) == {
        "max-age=0",
        "no-cache",
        "must-revalidate",
    }
    script_match = re.search(r'src="(/scripts/panel\.js\?v=([0-9a-f]{12}))"', html)
    style_match = re.search(r'href="(/styles/panel\.css\?v=([0-9a-f]{12}))"', html)
    assert script_match is not None
    assert style_match is not None

    script_response = client.get(script_match.group(1))
    assert script_response.status_code == 200
    assert script_response["Cache-Control"] == "public, max-age=31536000, immutable"


@pytest.mark.django_db
def test_unversioned_frontend_asset_is_revalidated(client):
    response = client.get("/scripts/panel.js")

    assert response.status_code == 200
    assert set(response["Cache-Control"].split(", ")) == {
        "max-age=0",
        "no-cache",
        "must-revalidate",
    }


@pytest.mark.django_db
def test_brand_assets_keep_a_moderate_cache_without_becoming_immutable(client):
    response = client.get("/brand/assets/logos/manifest.yaml")

    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=86400"
