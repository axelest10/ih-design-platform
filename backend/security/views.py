from rest_framework.decorators import api_view
from rest_framework.response import Response

from .permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ROLE_VIEWER,
)


@api_view(["GET"])
def current_user(request):
    user = request.user
    roles = list(user.groups.values_list("name", flat=True)) if user.is_authenticated else []
    role_set = set(roles)
    is_admin = bool(
        user.is_authenticated
        and (user.is_staff or user.is_superuser or ROLE_PLATFORM_ADMIN in role_set)
    )
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
        }
    )
