from django.db import migrations


def seed_brochure_document(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="brochure",
        defaults={
            "name": "Brochure A4",
            "renderer_family": "document",
            "channel": "print",
            "schema_version": "1.0.0",
            "supported_formats": ["a4"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    template_model.objects.update_or_create(
        key="brochure-a4-v1",
        defaults={
            "material_type": material_type,
            "version": "1.0.0",
            "dimensions": {
                "page_size": "A4",
                "width_mm": 210,
                "height_mm": 297,
            },
            "output_formats": ["pdf"],
            "required_fields": ["headline", "body", "cta"],
            "constraints": {
                "max_headline_chars": 120,
                "max_body_chars": 900,
                "max_cta_chars": 80,
                "approved_asset_required": True,
                "page_count": 1,
            },
            "active": True,
        },
    )


def remove_brochure_document(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    template_model.objects.filter(key="brochure-a4-v1").delete()
    material_type_model.objects.filter(slug="brochure").delete()


class Migration(migrations.Migration):
    dependencies = [("materials", "0003_social_post")]

    operations = [migrations.RunPython(seed_brochure_document, remove_brochure_document)]
