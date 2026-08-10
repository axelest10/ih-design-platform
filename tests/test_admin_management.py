import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from security.permissions import ROLE_PLATFORM_ADMIN


def _user(email, *, roles=(), is_staff=False):
    user = get_user_model().objects.create_user(
        username=email,
        email=email,
        is_staff=is_staff,
    )
    for role in roles:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_platform_admin_lists_paginated_corporate_users():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))
    _user("persona@ihbogota.com", roles=("viewer",))
    _user("external@example.com")

    response = _client(admin).get("/api/v1/security/users/")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    users = response.json()["results"]
    assert {user["email"] for user in users} == {
        "admin@ihmexico.com",
        "persona@ihbogota.com",
    }
    assert {"id", "email", "roles", "is_active", "date_joined", "last_login"} == set(
        users[0]
    )


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_platform_admin_adds_and_removes_valid_role():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))
    target = _user("persona@ihlima.com")
    client = _client(admin)
    url = f"/api/v1/security/users/{target.pk}/roles/"

    added = client.post(url, {"role": "designer", "action": "add"}, format="json")
    removed = client.post(url, {"role": "designer", "action": "remove"}, format="json")

    assert added.status_code == 200
    assert added.json()["roles"] == ["designer"]
    assert removed.status_code == 200
    assert removed.json()["roles"] == []


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_platform_admin_rejects_unknown_role():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))
    target = _user("persona@ihsantiago.cl")

    response = _client(admin).post(
        f"/api/v1/security/users/{target.pk}/roles/",
        {"role": "owner", "action": "add"},
        format="json",
    )

    assert response.status_code == 400
    assert "role" in response.json()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_admin_cannot_remove_own_platform_admin_role():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))
    _user("backup@ihbogota.com", roles=(ROLE_PLATFORM_ADMIN,))

    response = _client(admin).post(
        f"/api/v1/security/users/{admin.pk}/roles/",
        {"role": ROLE_PLATFORM_ADMIN, "action": "remove"},
        format="json",
    )

    assert response.status_code == 400
    assert "a ti mismo" in response.json()["detail"]
    assert admin.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_last_active_admin_role_cannot_be_removed():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))

    response = _client(admin).post(
        f"/api/v1/security/users/{admin.pk}/roles/",
        {"role": ROLE_PLATFORM_ADMIN, "action": "remove"},
        format="json",
    )

    assert response.status_code == 400
    assert "último acceso administrador" in response.json()["detail"]
    assert admin.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_admin_cannot_deactivate_own_account():
    admin = _user("admin@ihmexico.com", roles=(ROLE_PLATFORM_ADMIN,))

    response = _client(admin).patch(
        f"/api/v1/security/users/{admin.pk}/",
        {"is_active": False},
        format="json",
    )

    assert response.status_code == 400
    assert "propia cuenta" in response.json()["detail"]
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.corporate_auth
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("get", "/api/v1/security/users/", None),
        (
            "post",
            "/api/v1/security/users/{target}/roles/",
            {"role": "viewer", "action": "add"},
        ),
        ("patch", "/api/v1/security/users/{target}/", {"is_active": False}),
    ],
)
def test_non_admin_cannot_use_user_management_endpoints(method, url, payload):
    designer = _user("designer@ihmexico.com", roles=("designer",))
    target = _user("target@ihbogota.com")
    response = getattr(_client(designer), method)(
        url.format(target=target.pk),
        payload,
        format="json",
    )

    assert response.status_code == 403
