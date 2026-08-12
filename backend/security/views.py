from html import escape
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, update_session_auth_hash
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.observability import operation_event

from .permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    CorporateDomainPermission,
    can_create_briefs_user,
    is_allowed_corporate_email,
    is_platform_admin_user,
)
from .serializers import PasswordChangeSerializer, PasswordResetConfirmSerializer
from .services import (
    EmailDeliveryError,
    EmailMessage,
    PasswordResetError,
    consume_password_reset,
    create_password_reset,
    get_email_client,
    invalidate_other_password_resets,
)
from .throttles import LoginIPThrottle


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginIPThrottle])
def password_login(request):
    username = str(request.data.get("username") or "").strip()
    password = str(request.data.get("password") or "")
    user = authenticate(request=request, username=username, password=password)
    if user is None or not is_allowed_corporate_email(user.email):
        operation_event(
            "authentication.login",
            status="failed",
            reason="invalid_credentials_or_domain",
            http_status=401,
        )
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=401,
        )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    operation_event(
        "authentication.login",
        status="success",
        user_id=user.pk,
        http_status=200,
    )
    return Response({"authenticated": True, "username": user.get_username()})


PASSWORD_RESET_RESPONSE = {
    "detail": "Si la cuenta puede recuperar su acceso, recibirá un correo con instrucciones."
}


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginIPThrottle])
def request_password_reset(request):
    email = str(request.data.get("email") or "").strip().casefold()
    user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
    if not user or not is_allowed_corporate_email(user.email):
        return Response(PASSWORD_RESET_RESPONSE, status=202)
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        return Response(PASSWORD_RESET_RESPONSE, status=202)

    token, record = create_password_reset(user)
    reset_url = request.build_absolute_uri("/login.html") + f"#reset={quote(token, safe='')}"
    safe_url = escape(reset_url, quote=True)
    minutes = max(1, settings.PASSWORD_RESET_MAX_AGE_SECONDS // 60)
    message = EmailMessage(
        sender=settings.RESEND_FROM_EMAIL,
        recipients=(user.email,),
        subject="Recupera tu acceso a IH Design Platform",
        html=(
            f"<p>Usa este enlace para crear una contraseña nueva. Expira en {minutes} minutos "
            "y solo puede utilizarse una vez.</p>"
            f"<p><a href=\"{safe_url}\">Recuperar acceso</a></p>"
        ),
        text=(
            f"Usa este enlace para crear una contraseña nueva. Expira en {minutes} minutos y "
            f"solo puede utilizarse una vez.\n\n{reset_url}"
        ),
    )
    try:
        get_email_client().send(message)
    except EmailDeliveryError:
        record.delete()
        return Response(PASSWORD_RESET_RESPONSE, status=202)

    invalidate_other_password_resets(record)
    return Response(PASSWORD_RESET_RESPONSE, status=202)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginIPThrottle])
def confirm_password_reset(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        consume_password_reset(
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
        )
    except PasswordResetError as exc:
        return Response({"detail": str(exc)}, status=400)
    return Response({"detail": "Contraseña actualizada. Ya puedes iniciar sesión."})


@api_view(["POST"])
@permission_classes([IsAuthenticated, CorporateDomainPermission])
def change_password(request):
    serializer = PasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = request.user
    if not user.check_password(serializer.validated_data["current_password"]):
        return Response({"detail": "La contraseña actual no es correcta."}, status=400)

    user.set_password(serializer.validated_data["new_password"])
    user.save(update_fields=["password"])
    update_session_auth_hash(request, user)
    return Response({"detail": "Contraseña actualizada correctamente."})


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
