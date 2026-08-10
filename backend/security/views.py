from html import escape
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    is_allowed_corporate_email,
)
from .services import (
    EmailDeliveryError,
    EmailMessage,
    MagicLinkError,
    consume_magic_link,
    create_magic_link,
    get_email_client,
    invalidate_other_magic_links,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def request_magic_link(request):
    email = str(request.data.get("email") or "").strip().casefold()
    if not is_allowed_corporate_email(email):
        return Response({"detail": "El dominio del correo no está autorizado."}, status=400)
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        return Response({"detail": "El servicio de correo no está configurado."}, status=503)

    token, record = create_magic_link(email)
    verification_url = request.build_absolute_uri(
        f"/verify.html?{urlencode({'token': token})}"
    )
    safe_url = escape(verification_url, quote=True)
    max_age = settings.MAGIC_LINK_MAX_AGE_SECONDS
    expiration_text = (
        f"{max_age // 60} minutos" if max_age % 60 == 0 else f"{max_age} segundos"
    )
    message = EmailMessage(
        sender=settings.RESEND_FROM_EMAIL,
        recipients=(email,),
        subject="Tu enlace de acceso a IH Design Platform",
        html=(
            f"<p>Usa este enlace para iniciar sesión. Expira en {expiration_text} y solo puede "
            f"utilizarse una vez.</p><p><a href=\"{safe_url}\">Iniciar sesión</a></p>"
        ),
        text=(
            f"Usa este enlace para iniciar sesión. Expira en {expiration_text} y solo puede "
            f"utilizarse una vez.\n\n{verification_url}"
        ),
    )
    try:
        get_email_client().send(message)
    except EmailDeliveryError:
        record.delete()
        return Response({"detail": "No fue posible enviar el enlace de acceso."}, status=502)

    invalidate_other_magic_links(record)
    return Response(
        {"detail": "Si el correo está autorizado, recibirás un enlace de acceso."},
        status=202,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_magic_link(request):
    token = str(request.query_params.get("token") or "").strip()
    if not token:
        return Response({"detail": "Falta el token del enlace de acceso."}, status=400)
    try:
        user = consume_magic_link(token)
    except MagicLinkError as exc:
        return Response({"detail": str(exc)}, status=400)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return Response({"authenticated": True, "email": user.email})


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
