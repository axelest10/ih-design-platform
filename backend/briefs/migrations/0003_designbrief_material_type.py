import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("briefs", "0002_designbrief_additional_logo_keys_and_more"),
        ("materials", "0002_school_kit"),
    ]

    operations = [
        migrations.AddField(
            model_name="designbrief",
            name="material_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="briefs",
                to="materials.materialtype",
            ),
        ),
    ]
