from django.db import migrations


def seed_email_kit(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="email-kit",
        defaults={
            "name": "Paquetería de marketing para email",
            "renderer_family": "email-html",
            "channel": "email",
            "schema_version": "1.0.0",
            "supported_formats": ["html"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    template_model.objects.update_or_create(
        key="email-base-v1",
        defaults={
            "material_type": material_type,
            "version": "1.0.0",
            "dimensions": {"max_width_px": 640},
            "output_formats": ["html"],
            "required_fields": [
                "subject",
                "preheader",
                "headline",
                "body",
                "cta_label",
                "cta_url",
                "unsubscribe_url",
            ],
            "field_labels": {
                "subject": "Asunto",
                "preheader": "Preheader",
                "headline": "Titular",
                "body": "Cuerpo",
                "cta_label": "Texto del CTA",
                "cta_url": "URL del CTA",
                "unsubscribe_url": "URL de baja",
            },
            "constraints": {
                "max_subject_chars": 150,
                "max_preheader_chars": 180,
                "max_headline_chars": 120,
                "max_body_chars": 1800,
                "max_cta_label_chars": 80,
                "uses_inline_css": True,
                "uses_tables": True,
                "max_width_px": 640,
                "allows_sending": False,
            },
            "active": True,
        },
    )


def remove_email_kit(apps, schema_editor):
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model.objects.filter(key="email-base-v1").delete()
    material_type_model.objects.filter(slug="email-kit").delete()


class Migration(migrations.Migration):
    dependencies = [("materials", "0012_sales_kit")]
    operations = [migrations.RunPython(seed_email_kit, remove_email_kit)]
