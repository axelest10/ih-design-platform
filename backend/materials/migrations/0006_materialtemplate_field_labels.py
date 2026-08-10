from django.db import migrations, models


FIELD_LABELS = {
    "square-v1": {"headline": "Título principal", "body": "Texto del cuerpo"},
    "story-v1": {"headline": "Título principal", "body": "Texto del cuerpo"},
    "portrait-v1": {"headline": "Título principal", "body": "Texto del cuerpo"},
    "brochure-a4-v1": {
        "headline": "Título principal",
        "body": "Texto del cuerpo",
        "cta": "Llamada a la acción",
    },
    "presentation-16x9-v1": {
        "headline": "Título de la diapositiva",
        "body": "Contenido principal",
        "cta": "Llamada a la acción",
    },
    "school-kit-v1": {
        "name": "Nombre del paquete",
        "country": "País",
        "product_slugs": "Productos",
    },
}


def populate_field_labels(apps, schema_editor):
    template_model = apps.get_model("materials", "MaterialTemplate")
    for key, labels in FIELD_LABELS.items():
        template_model.objects.filter(key=key).update(field_labels=labels)


def clear_field_labels(apps, schema_editor):
    template_model = apps.get_model("materials", "MaterialTemplate")
    template_model.objects.filter(key__in=FIELD_LABELS).update(field_labels={})


class Migration(migrations.Migration):
    dependencies = [("materials", "0005_presentation_template")]

    operations = [
        migrations.AddField(
            model_name="materialtemplate",
            name="field_labels",
            field=models.JSONField(default=dict),
        ),
        migrations.RunPython(populate_field_labels, clear_field_labels),
    ]
