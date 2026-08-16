from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("designs", "0004_asyncgenerationjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="designversion",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("approved", "Aprobado"),
                    ("rejected", "Rechazado"),
                    ("changes_requested", "Cambios solicitados"),
                ],
                default="pending",
                max_length=24,
            ),
        ),
    ]
