import json
from pathlib import Path

from jsonschema import Draft202012Validator
from rest_framework import serializers

from .models import BriefReferenceUpload, DesignBrief
from .services.generation import SUPPORTED_BRIEF_FORMATS
from .services.options import (
    PRIMARY_PRODUCT_SLUGS,
    is_regional_admin,
    validate_brief_logo_access,
    validate_uploaded_logo_access,
)


def validate_brief_contract(data):
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "design-brief.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda error: error.path)
    if errors:
        raise serializers.ValidationError({"contract": [error.message for error in errors]})


class DesignBriefSerializer(serializers.ModelSerializer):
    authorized_color = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DesignBrief
        fields = "__all__"
        read_only_fields = ("created_by", "authorized_color")

    def get_authorized_color(self, obj):
        from .services.options import primary_products

        product = next(
            (item for item in primary_products() if item["product_slug"] == obj.product_slug),
            None,
        )
        return product.get("authorized_color", {}) if product else {}

    def validate(self, attrs):
        instance = self.instance
        brief_format = attrs.get("format", instance.format if instance else None)
        if brief_format not in SUPPORTED_BRIEF_FORMATS:
            raise serializers.ValidationError(
                {
                    "format": (
                        f"El formato '{brief_format}' no está disponible todavía. "
                        "Por ahora solo se pueden generar square, story y portrait."
                    )
                }
            )
        payload = {
            "title": attrs.get("title", instance.title if instance else None),
            "format": brief_format,
            "audience": attrs.get("audience", instance.audience if instance else None),
            "objective": attrs.get("objective", instance.objective if instance else None),
            "requested_message": attrs.get(
                "requested_message", instance.requested_message if instance else ""
            ),
            "source_references": attrs.get(
                "source_references", instance.source_references if instance else []
            ),
            "constraints": attrs.get("constraints", instance.constraints if instance else {}),
        }
        validate_brief_contract(payload)
        product_slug = attrs.get(
            "product_slug", instance.product_slug if instance else ""
        )
        if product_slug and product_slug not in PRIMARY_PRODUCT_SLUGS:
            raise serializers.ValidationError(
                {"product_slug": "Selecciona uno de los cinco productos principales."}
            )

        country = attrs.get("country", instance.country if instance else "")
        brand_logo_key = attrs.get(
            "brand_logo_key", instance.brand_logo_key if instance else ""
        )
        request = self.context.get("request")
        user = request.user if request else None
        if brand_logo_key:
            error = validate_brief_logo_access(brand_logo_key, country, user)
            if error:
                raise serializers.ValidationError({"brand_logo_key": error})

        additional_logo_keys = attrs.get(
            "additional_logo_keys",
            instance.additional_logo_keys if instance else [],
        )
        if len(additional_logo_keys) > 3:
            raise serializers.ValidationError(
                {"additional_logo_keys": "Puedes agregar hasta tres logos adicionales."}
            )
        for key in additional_logo_keys:
            if str(key).startswith("uploaded:"):
                upload_key = str(key).split(":", 1)[1]
                if not validate_uploaded_logo_access(upload_key, user):
                    raise serializers.ValidationError(
                        {"additional_logo_keys": f"No puedes usar el logo subido '{key}'."}
                    )
            else:
                error = validate_brief_logo_access(str(key), country, user)
                if error:
                    raise serializers.ValidationError({"additional_logo_keys": error})
        return attrs


class BriefReferenceUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefReferenceUpload
        fields = "__all__"
        read_only_fields = ("created_by",)

    def validate(self, attrs):
        request = self.context.get("request")
        brief = attrs.get("brief")
        user = request.user if request else None
        if brief and user and user.is_authenticated:
            if not is_regional_admin(user) and brief.created_by_id != user.pk:
                raise serializers.ValidationError(
                    {"brief": "Solo puedes adjuntar referencias a tus propios briefs."}
                )
        file = attrs.get("file")
        if file and file.size > 15 * 1024 * 1024:
            raise serializers.ValidationError({"file": "La referencia no puede superar 15 MB."})
        return attrs
