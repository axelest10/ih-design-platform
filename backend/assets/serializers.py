from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import ArtworkReference, OfficialAsset, UploadedLogo


class OfficialAssetSerializer(ModelSerializer):
    class Meta:
        model = OfficialAsset
        fields = "__all__"


class ArtworkReferenceSerializer(ModelSerializer):
    class Meta:
        model = ArtworkReference
        fields = "__all__"
        read_only_fields = ("created_by", "checksum")

    def validate(self, attrs):
        request = self.context.get("request")
        reference_type = attrs.get(
            "reference_type",
            self.instance.reference_type
            if self.instance
            else ArtworkReference.ReferenceType.INSPIRATION,
        )
        source_url = attrs.get("source_url", self.instance.source_url if self.instance else "")
        source_folder_url = attrs.get(
            "source_folder_url", self.instance.source_folder_url if self.instance else ""
        )
        file = attrs.get("file", self.instance.file if self.instance else None)
        if reference_type == ArtworkReference.ReferenceType.APPROVED_BASE and not any(
            (file, source_url, source_folder_url)
        ):
            raise serializers.ValidationError(
                "Una base aprobada debe tener archivo, source_url o source_folder_url."
            )

        approval_status = attrs.get(
            "approval_status",
            self.instance.approval_status
            if self.instance
            else ArtworkReference.ApprovalStatus.PENDING,
        )
        if approval_status == ArtworkReference.ApprovalStatus.APPROVED and request:
            user = request.user
            can_approve = user.is_authenticated and (
                user.is_staff
                or user.is_superuser
                or user.groups.filter(name__in=("platform_admin", "reviewer")).exists()
            )
            if not can_approve:
                raise serializers.ValidationError(
                    "Solo un reviewer o platform_admin puede aprobar una referencia."
                )
        return attrs


class UploadedLogoSerializer(ModelSerializer):
    class Meta:
        model = UploadedLogo
        fields = "__all__"
        read_only_fields = ("key", "created_by", "status")
