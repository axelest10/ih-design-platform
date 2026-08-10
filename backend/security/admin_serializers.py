from django.contrib.auth import get_user_model
from rest_framework import serializers

from .permissions import CORPORATE_ROLES


class CorporateUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "roles", "is_active", "date_joined", "last_login")

    def get_roles(self, obj):
        return sorted(obj.groups.values_list("name", flat=True))


class UserRoleMutationSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=CORPORATE_ROLES)
    action = serializers.ChoiceField(choices=("add", "remove"))


class UserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=True)
