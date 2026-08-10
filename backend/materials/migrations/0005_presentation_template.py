from django.db import migrations, models


def seed_presentation_template(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="presentation",
        defaults={
            "name": "Presentación corporativa",
            "renderer_family": "presentation",
            "channel": "presentation",
            "schema_version": "1.0.0",
            "supported_formats": ["16:9"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    template_model.objects.update_or_create(
        key="presentation-16x9-v1",
        defaults={
            "material_type": material_type,
            "version": "1.0.0",
            "dimensions": {
                "ratio": "16:9",
                "width_in": 13.333,
                "height_in": 7.5,
            },
            "output_formats": ["pptx"],
            "required_fields": ["headline", "body", "cta"],
            "constraints": {
                "layout": "title-content",
                "max_headline_chars": 100,
                "max_body_chars": 500,
                "max_cta_chars": 80,
                "approved_asset_required": True,
                "slide_count": 1,
            },
            "active": True,
        },
    )


def remove_presentation_template(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    template_model.objects.filter(key="presentation-16x9-v1").delete()
    material_type_model.objects.filter(slug="presentation").delete()


class Migration(migrations.Migration):
    dependencies = [("materials", "0004_brochure_document")]

    operations = [
        migrations.AlterField(
            model_name="materialtype",
            name="renderer_family",
            field=models.CharField(
                choices=[
                    ("html-svg", "HTML/SVG"),
                    ("email-html", "Email HTML"),
                    ("document", "Documento"),
                    ("presentation", "Presentación"),
                ],
                max_length=32,
            ),
        ),
        migrations.RunPython(seed_presentation_template, remove_presentation_template),
    ]
