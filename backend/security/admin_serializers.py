from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from .permissions import CORPORATE_ROLES, is_allowed_corporate_email


class CorporateUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "roles",
            "is_active",
            "date_joined",
            "last_login",
        )

    def get_roles(self, obj):
        return sorted(obj.groups.values_list("name", flat=True))


class UserRoleMutationSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=CORPORATE_ROLES)
    action = serializers.ChoiceField(choices=("add", "remove"))


class UserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=True)


class CorporateUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=CORPORATE_ROLES),
        allow_empty=True,
    )

    def validate_username(self, value):
        normalized = value.strip()
        if get_user_model().objects.filter(username__iexact=normalized).exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre.")
        return normalized

    def validate_email(self, value):
        normalized = value.strip().casefold()
        if not is_allowed_corporate_email(normalized):
            raise serializers.ValidationError("El dominio del correo no está autorizado.")
        if get_user_model().objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return normalized

    def create(self, validated_data):
        roles = validated_data.pop("roles")
        user = get_user_model().objects.create_user(**validated_data)
        groups = [Group.objects.get_or_create(name=role)[0] for role in roles]
        user.groups.add(*groups)
        return user


class UserPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
