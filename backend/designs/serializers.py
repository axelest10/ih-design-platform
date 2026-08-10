from rest_framework import serializers

from .models import Design, DesignReviewComment, DesignVersion


class DesignVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignVersion
        fields = "__all__"


class DesignSerializer(serializers.ModelSerializer):
    versions = DesignVersionSerializer(many=True, read_only=True)
    brief_title = serializers.CharField(source="brief.title", read_only=True)
    brief_product_slug = serializers.CharField(source="brief.product_slug", read_only=True)

    class Meta:
        model = Design
        fields = (
            "id",
            "brief",
            "brief_title",
            "brief_product_slug",
            "status",
            "approved_version",
            "test_number",
            "created_at",
            "updated_at",
            "versions",
        )


class DesignReviewCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = DesignReviewComment
        fields = ("id", "design", "version", "author", "author_email", "comment", "created_at")
        read_only_fields = ("design", "author")

    def validate_comment(self, value):
        comment = value.strip()
        if not comment:
            raise serializers.ValidationError("Escribe un comentario antes de guardarlo.")
        return comment

    def validate_version(self, version):
        design = self.context.get("design")
        if version is not None and design is not None and version.design_id != design.pk:
            raise serializers.ValidationError("La versión no pertenece a este diseño.")
        return version
