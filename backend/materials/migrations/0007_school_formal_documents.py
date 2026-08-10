from django.db import migrations

TEMPLATES = (
    {
        "key": "letter-a4-v1",
        "required_fields": ["sender", "recipient", "body", "signature"],
        "field_labels": {
            "sender": "Remitente",
            "recipient": "Destinatario",
            "body": "Cuerpo de la carta",
            "signature": "Firma",
        },
        "constraints": {
            "layout": "formal-letter",
            "max_sender_chars": 100,
            "max_recipient_chars": 140,
            "max_body_chars": 1800,
            "max_signature_chars": 120,
        },
    },
    {
        "key": "announcement-a4-v1",
        "required_fields": ["headline", "date", "body", "contact"],
        "field_labels": {
            "headline": "Titular del anuncio",
            "date": "Fecha o vigencia",
            "body": "Información del anuncio",
            "contact": "Datos de contacto",
        },
        "constraints": {
            "layout": "announcement",
            "max_headline_chars": 100,
            "max_date_chars": 80,
            "max_body_chars": 1000,
            "max_contact_chars": 140,
        },
    },
    {
        "key": "flyer-a4-v1",
        "required_fields": ["headline", "subtitle", "body", "cta", "contact"],
        "field_labels": {
            "headline": "Título principal",
            "subtitle": "Subtítulo",
            "body": "Información principal",
            "cta": "Llamada a la acción",
            "contact": "Datos de contacto",
        },
        "constraints": {
            "layout": "flyer",
            "max_headline_chars": 100,
            "max_subtitle_chars": 120,
            "max_body_chars": 900,
            "max_cta_chars": 80,
            "max_contact_chars": 140,
        },
    },
)


def seed_school_documents(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    material_type, _ = material_type_model.objects.update_or_create(
        slug="school-documents",
        defaults={
            "name": "Documentos formales para colegios",
            "renderer_family": "document",
            "channel": "school",
            "schema_version": "1.0.0",
            "supported_formats": ["a4"],
            "priority_product_slugs": [],
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    dimensions = {"page_size": "A4", "width_mm": 210, "height_mm": 297}
    for item in TEMPLATES:
        template_model.objects.update_or_create(
            key=item["key"],
            defaults={
                "material_type": material_type,
                "version": "1.0.0",
                "dimensions": dimensions,
                "output_formats": ["pdf"],
                "required_fields": item["required_fields"],
                "field_labels": item["field_labels"],
                "constraints": {
                    **item["constraints"],
                    "approved_asset_required": True,
                    "page_count": 1,
                },
                "active": True,
            },
        )
    brochure = template_model.objects.filter(key="brochure-a4-v1").first()
    if brochure:
        brochure.constraints = {**(brochure.constraints or {}), "layout": "brochure"}
        brochure.save(update_fields=["constraints"])


def remove_school_documents(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    template_model = apps.get_model("materials", "MaterialTemplate")
    template_model.objects.filter(key__in=[item["key"] for item in TEMPLATES]).delete()
    material_type_model.objects.filter(slug="school-documents").delete()
    brochure = template_model.objects.filter(key="brochure-a4-v1").first()
    if brochure:
        constraints = dict(brochure.constraints or {})
        constraints.pop("layout", None)
        brochure.constraints = constraints
        brochure.save(update_fields=["constraints"])


class Migration(migrations.Migration):
    dependencies = [("materials", "0006_materialtemplate_field_labels")]

    operations = [migrations.RunPython(seed_school_documents, remove_school_documents)]
