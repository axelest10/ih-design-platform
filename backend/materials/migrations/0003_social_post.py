from django.db import migrations


SOCIAL_POST_TEMPLATES = (
    {
        "key": "square-v1",
        "format": "square",
        "dimensions": [1080, 1080],
        "html_file": "designs/square-v1.html",
        "svg_file": "designs/square-v1.svg",
    },
    {
        "key": "story-v1",
        "format": "story",
        "dimensions": [1080, 1920],
        "html_file": "designs/story-v1.html",
        "svg_file": "designs/story-v1.svg",
    },
    {
        "key": "portrait-v1",
        "format": "portrait",
        "dimensions": [1080, 1350],
        "html_file": "designs/portrait-v1.html",
        "svg_file": "designs/portrait-v1.svg",
    },
)


def seed_social_post(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="social-post",
        defaults={
            "name": "Publicación para redes sociales",
            "renderer_family": "html-svg",
            "channel": "instagram",
            "schema_version": "1.0.0",
            "supported_formats": ["square", "story", "portrait"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    for template in SOCIAL_POST_TEMPLATES:
        template_model.objects.update_or_create(
            key=template["key"],
            defaults={
                "material_type": material_type,
                "version": "1.0.0",
                "dimensions": template["dimensions"],
                "output_formats": ["html", "svg"],
                "required_fields": ["headline", "body"],
                "constraints": {
                    "format": template["format"],
                    "html_file": template["html_file"],
                    "svg_file": template["svg_file"],
                    "approved_asset_required": True,
                    "review_flow": "designs-preview-and-review",
                },
                "active": True,
            },
        )


def remove_social_post(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    template_model.objects.filter(
        material_type__slug="social-post",
        key__in=[template["key"] for template in SOCIAL_POST_TEMPLATES],
    ).delete()
    material_type_model.objects.filter(slug="social-post").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("briefs", "0003_designbrief_material_type"),
        ("materials", "0002_school_kit"),
    ]

    operations = [migrations.RunPython(seed_social_post, remove_social_post)]
