from pathlib import Path
from urllib.parse import quote

from django.urls import reverse
from rest_framework import serializers

from .models import (
    MarketingAsset,
    MaterialBundle,
    MaterialBundleItem,
    MaterialTemplate,
    MaterialType,
)
from .services.catalog import sales_kit_products, school_kit_products
from .services.sales_kit import sales_kit_deliverables
from .services.school_kit import school_kit_deliverables


class MaterialTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialTemplate
        fields = "__all__"


class MarketingAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    brand_label = serializers.CharField(source="get_brand_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = MarketingAsset
        fields = "__all__"
        read_only_fields = ("uploaded_by", "created_at", "file_url")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        filename = quote(Path(obj.file.name).name)
        return reverse("marketing-asset-file", args=[obj.pk, filename])

    def validate_country(self, value):
        return value.strip().upper()

    def validate_file(self, value):
        if value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("El archivo no puede superar 25 MB.")
        return value


class MaterialTypeSerializer(serializers.ModelSerializer):
    available_products = serializers.SerializerMethodField()
    default_deliverables = serializers.SerializerMethodField()

    class Meta:
        model = MaterialType
        fields = (
            "id",
            "slug",
            "name",
            "renderer_family",
            "channel",
            "schema_version",
            "supported_formats",
            "priority_product_slugs",
            "product_scope",
            "active",
            "created_at",
            "updated_at",
            "available_products",
            "default_deliverables",
        )

    def get_available_products(self, obj):
        if obj.slug == "sales-kit":
            return sales_kit_products()
        if obj.slug != "school-kit":
            return []
        request = self.context.get("request")
        country = request.query_params.get("country", "") if request else ""
        return school_kit_products(country=country, priority=obj.priority_product_slugs)

    def get_default_deliverables(self, obj):
        if obj.slug == "sales-kit":
            return sales_kit_deliverables()
        return school_kit_deliverables() if obj.slug == "school-kit" else []


class MaterialBundleItemSerializer(serializers.ModelSerializer):
    design = serializers.SerializerMethodField()

    class Meta:
        model = MaterialBundleItem
        fields = ("id", "bundle", "brief", "deliverable_key", "sort_order", "design")

    def get_design(self, obj):
        design = getattr(obj.brief, "design", None)
        if design is None:
            return None
        latest_version = design.versions.first()
        return {
            "id": design.pk,
            "status": design.status,
            "test_number": design.test_number,
            "latest_version": latest_version.number if latest_version else None,
            "claude_review_status": (
                latest_version.claude_review_status if latest_version else None
            ),
            "claude_review": latest_version.claude_review if latest_version else {},
        }


class MaterialBundleSerializer(serializers.ModelSerializer):
    items = MaterialBundleItemSerializer(many=True, read_only=True)
    priority_products = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MaterialBundle
        fields = "__all__"
        read_only_fields = ("created_by", "priority_products")

    def get_priority_products(self, obj):
        material_type = obj.material_type
        return [slug for slug in material_type.priority_product_slugs if slug in obj.product_slugs]

    def validate(self, attrs):
        material_type = attrs.get(
            "material_type", self.instance.material_type if self.instance else None
        )
        if material_type is None or not material_type.active:
            raise serializers.ValidationError(
                {"material_type": "El tipo de material no está activo."}
            )
        product_slugs = attrs.get(
            "product_slugs", self.instance.product_slugs if self.instance else []
        )
        if material_type.slug == "school-kit":
            available = {item["product_slug"] for item in school_kit_products()}
            invalid = sorted(set(product_slugs) - available)
            if invalid:
                raise serializers.ValidationError(
                    {"product_slugs": f"Productos fuera del catálogo activo: {', '.join(invalid)}."}
                )
            if not product_slugs:
                raise serializers.ValidationError(
                    {"product_slugs": "Selecciona al menos un producto para la paquetería."}
                )
        elif material_type.slug == "sales-kit":
            campaign = attrs.get(
                "campaign", self.instance.campaign if self.instance else None
            )
            if campaign is None:
                raise serializers.ValidationError(
                    {"campaign": "Selecciona una campaña comercial autorizada."}
                )
            if not product_slugs and campaign.product_id:
                product_slugs = [campaign.product.code]
                attrs["product_slugs"] = product_slugs
            available = {item["product_slug"] for item in sales_kit_products()}
            invalid = sorted(set(product_slugs) - available)
            if invalid:
                raise serializers.ValidationError(
                    {"product_slugs": f"Productos fuera del catálogo activo: {', '.join(invalid)}."}
                )
            if not product_slugs:
                raise serializers.ValidationError(
                    {"product_slugs": "Selecciona al menos un producto para la paquetería."}
                )
            if campaign.product_id and set(product_slugs) != {campaign.product.code}:
                raise serializers.ValidationError(
                    {
                        "product_slugs": (
                            "La campaña solo puede generar el producto que tiene asociado."
                        )
                    }
                )
        return attrs
