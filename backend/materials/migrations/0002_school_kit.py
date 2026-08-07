from django.db import migrations


def seed_school_kit(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="school-kit",
        defaults={
            "name": "Paquetería de marketing para colegios",
            "renderer_family": "html-svg",
            "channel": "school",
            "schema_version": "1.0.0",
            "supported_formats": ["square", "story", "portrait"],
            "priority_product_slugs": [
                "qc-2026",
                "teacher-training-certifications",
            ],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    template_model.objects.update_or_create(
        key="school-kit-v1",
        defaults={
            "material_type": material_type,
            "version": "1.0.0",
            "dimensions": {
                "square": [1080, 1080],
                "story": [1080, 1920],
                "portrait": [1080, 1350],
            },
            "output_formats": ["html", "svg"],
            "required_fields": ["name", "country", "product_slugs"],
            "constraints": {"uses_active_product_catalog": True},
            "active": True,
        },
    )


def remove_school_kit(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    material_type_model.objects.filter(slug="school-kit").delete()


class Migration(migrations.Migration):
    dependencies = [("materials", "0001_initial")]

    operations = [migrations.RunPython(seed_school_kit, remove_school_kit)]
