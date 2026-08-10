from django.conf import settings
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    can_create_briefs_user,
    is_allowed_corporate_email,
    is_platform_admin_user,
)
from .throttles import LoginIPThrottle


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginIPThrottle])
def password_login(request):
    username = str(request.data.get("username") or "").strip()
    password = str(request.data.get("password") or "")
    user = authenticate(request=request, username=username, password=password)
    if user is None or not is_allowed_corporate_email(user.email):
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=401,
        )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return Response({"authenticated": True, "username": user.get_username()})


@api_view(["GET"])
def current_user(request):
    user = request.user
    roles = list(user.groups.values_list("name", flat=True)) if user.is_authenticated else []
    role_set = set(roles)
    is_admin = is_platform_admin_user(user)
    return Response(
        {
            "authenticated": user.is_authenticated,
            "username": user.get_username() if user.is_authenticated else None,
            "email": user.email if user.is_authenticated else None,
            "roles": roles,
            "is_admin": is_admin,
            "can_create_briefs": can_create_briefs_user(user),
            "can_review": bool(is_admin or ROLE_REVIEWER in role_set),
            "can_view_catalog": bool(
                is_admin
                or role_set.intersection(
                    {ROLE_MARKETING, ROLE_DESIGNER, ROLE_REVIEWER, ROLE_VIEWER}
                )
            ),
            "regional_brand_access": is_admin,
            "available_panels": ["admin", "user"] if is_admin else ["user"],
            "design_test_mode": settings.DESIGN_TEST_MODE,
            "design_test_limit": settings.DESIGN_TEST_LIMIT,
        }
    )
