from django.db import migrations


def seed_sales_kit(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    material_type_model.objects.update_or_create(
        slug="sales-kit",
        defaults={
            "name": "Paquetería de marketing para ventas",
            "renderer_family": "html-svg",
            "channel": "sales",
            "schema_version": "1.0.0",
            "supported_formats": ["square", "story", "portrait", "a4", "16:9"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )


def remove_sales_kit(apps, schema_editor):
    apps.get_model("materials", "MaterialType").objects.filter(slug="sales-kit").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("briefs", "0005_presentation_format"),
        ("materials", "0009_alter_marketingasset_file"),
    ]

    operations = [migrations.RunPython(seed_sales_kit, remove_sales_kit)]
