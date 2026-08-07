import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("path, marker", [("/", "Design Platform"), ("/panel.html", "brief-form")])
def test_frontend_pages_are_served(client, path, marker):
    response = client.get(path)

    assert response.status_code == 200
    assert marker.encode() in response.content


@pytest.mark.django_db
def test_admin_page_is_served(client):
    response = client.get("/admin.html")

    assert response.status_code == 200
    assert b"Panel administrador" in response.content
