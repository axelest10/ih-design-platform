from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.crypto import constant_time_compare
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    is_platform_admin_user,
)
from .throttles import SiteAccessIPThrottle

SHARED_ACCESS_USERNAME = "shared-access"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([SiteAccessIPThrottle])
def site_access(request):
    configured_password = settings.SITE_ACCESS_PASSWORD
    if not configured_password:
        return Response(
            {"detail": "El acceso interno no está configurado."},
            status=503,
        )

    submitted_password = str(request.data.get("password") or "")
    if not constant_time_compare(submitted_password, configured_password):
        return Response({"detail": "No fue posible iniciar sesión."}, status=401)

    user = get_user_model().objects.filter(username=SHARED_ACCESS_USERNAME).first()
    if user is None or not user.is_active:
        return Response(
            {"detail": "El acceso interno no está disponible."},
            status=503,
        )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return Response({"authenticated": True})


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
            "can_create_briefs": bool(
                is_admin or role_set.intersection({ROLE_MARKETING, ROLE_DESIGNER})
            ),
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
