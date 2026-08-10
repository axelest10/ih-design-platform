from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .admin_serializers import (
    CorporateUserSerializer,
    UserRoleMutationSerializer,
    UserStatusSerializer,
)
from .permissions import (
    ROLE_PLATFORM_ADMIN,
    CorporateDomainPermission,
    PlatformAdminPermission,
)


class CorporateUserPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _corporate_users():
    domains = settings.CORPORATE_ALLOWED_EMAIL_DOMAINS
    filters = [Q(email__iendswith=f"@{domain}") for domain in domains]
    if not filters:
        return get_user_model().objects.none()
    return (
        get_user_model()
        .objects.filter(reduce(or_, filters))
        .prefetch_related("groups")
        .order_by("email", "pk")
    )


def _active_admin_count() -> int:
    return (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(
            Q(is_staff=True)
            | Q(is_superuser=True)
            | Q(groups__name=ROLE_PLATFORM_ADMIN)
        )
        .distinct()
        .count()
    )


ADMIN_PERMISSIONS = (CorporateDomainPermission, PlatformAdminPermission)


@api_view(["GET"])
@permission_classes(ADMIN_PERMISSIONS)
def corporate_user_list(request):
    paginator = CorporateUserPagination()
    page = paginator.paginate_queryset(_corporate_users(), request)
    serializer = CorporateUserSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["POST"])
@permission_classes(ADMIN_PERMISSIONS)
def corporate_user_roles(request, user_id):
    serializer = UserRoleMutationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target = get_object_or_404(get_user_model(), pk=user_id)
    role = serializer.validated_data["role"]
    action = serializer.validated_data["action"]

    if action == "remove" and role == ROLE_PLATFORM_ADMIN:
        target_has_group = target.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()
        target_stays_admin = target.is_staff or target.is_superuser
        if target_has_group and not target_stays_admin and _active_admin_count() <= 1:
            return Response(
                {
                    "detail": (
                        "No puedes quitar el último acceso administrador; la plataforma "
                        "quedaría sin administradores activos."
                    )
                },
                status=400,
            )
        if target.pk == request.user.pk:
            return Response(
                {"detail": "No puedes quitarte a ti mismo el rol platform_admin."},
                status=400,
            )

    group, _ = Group.objects.get_or_create(name=role)
    if action == "add":
        target.groups.add(group)
    else:
        target.groups.remove(group)
    return Response(CorporateUserSerializer(target).data)


@api_view(["PATCH"])
@permission_classes(ADMIN_PERMISSIONS)
def corporate_user_detail(request, user_id):
    serializer = UserStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target = get_object_or_404(get_user_model(), pk=user_id)
    is_active = serializer.validated_data["is_active"]
    if target.pk == request.user.pk and not is_active:
        return Response(
            {"detail": "No puedes desactivar tu propia cuenta administrativa."},
            status=400,
        )
    target.is_active = is_active
    target.save(update_fields=["is_active"])
    return Response(CorporateUserSerializer(target).data)
