from html import escape
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.utils import timezone
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.observability import operation_event

from .models import EmailRecipientState, TransactionalEmailDelivery
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
    EmailDeliverySuppressed,
    PasswordResetError,
    consume_password_reset,
    create_password_reset,
    invalidate_other_password_resets,
    send_transactional_email,
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def session_logout(request):
    user_id = request.user.pk
    logout(request)
    operation_event(
        "authentication.logout",
        status="success",
        user_id=user_id,
        http_status=200,
    )
    return Response({"authenticated": False})


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
    token, record = create_password_reset(user)
    delivery = TransactionalEmailDelivery.objects.create(
        recipient=user.email.strip().casefold(),
        user=user,
        password_reset_token=record,
        message_stream=settings.POSTMARK_MESSAGE_STREAM,
        tag="password-reset",
    )
    reset_url = request.build_absolute_uri("/login.html") + f"#reset={quote(token, safe='')}"
    safe_url = escape(reset_url, quote=True)
    minutes = max(1, settings.PASSWORD_RESET_MAX_AGE_SECONDS // 60)
    try:
        provider_message_id = send_transactional_email(
            to=user.email,
            subject="Recupera tu acceso a IH Design Platform",
            html_body=(
                f"<p>Usa este enlace para crear una contraseña nueva. "
                f"Expira en {minutes} minutos y solo puede utilizarse una vez.</p>"
                f'<p><a href="{safe_url}">Recuperar acceso</a></p>'
            ),
            text_body=(
                f"Usa este enlace para crear una contraseña nueva. "
                f"Expira en {minutes} minutos y solo puede utilizarse una vez.\n\n{reset_url}"
            ),
            tag="password-reset",
            metadata={"email_delivery_id": str(delivery.pk)},
        )
    except EmailDeliverySuppressed as exc:
        delivery.password_reset_token = None
        record.delete()
        delivery.refresh_from_db()
        if delivery.last_event_at is None:
            delivery.status = TransactionalEmailDelivery.Status.SUPPRESSED
            delivery.failure_category = exc.category
            delivery.suppressed = exc.category == "recipient_provider_suppressed"
        delivery.save()
        operation_event(
            "authentication.password_reset_email",
            status="suppressed",
            provider="postmark",
            reason=exc.category,
            user_id=user.pk,
            http_status=202,
        )
        return Response(PASSWORD_RESET_RESPONSE, status=202)
    except EmailDeliveryError as exc:
        delivery.password_reset_token = None
        record.delete()
        delivery.refresh_from_db()
        if delivery.last_event_at is None:
            delivery.status = TransactionalEmailDelivery.Status.FAILED
            delivery.failure_category = exc.category
        delivery.save()
        operation_event(
            "authentication.password_reset_email",
            status="failed",
            provider="postmark",
            reason=exc.category,
            user_id=user.pk,
            http_status=202,
        )
        return Response(PASSWORD_RESET_RESPONSE, status=202)

    invalidate_other_password_resets(record)
    delivery.provider_message_id = provider_message_id
    delivery.accepted_at = timezone.now()
    if delivery.last_event_at is None:
        delivery.status = TransactionalEmailDelivery.Status.ACCEPTED
    delivery.save()
    EmailRecipientState.objects.get_or_create(recipient=delivery.recipient)
    operation_event(
        "authentication.password_reset_email",
        status="accepted",
        provider="postmark",
        provider_message_id=provider_message_id,
        email_delivery_id=delivery.pk,
        user_id=user.pk,
        http_status=202,
    )
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
