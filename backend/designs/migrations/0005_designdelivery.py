from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("designs", "0004_asyncgenerationjob"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DesignDelivery",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "recipient_email",
                    models.EmailField(blank=True, max_length=254),
                ),
                ("channel", models.CharField(default="email", max_length=24)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "En cola"),
                            ("processing", "Procesando"),
                            ("delivered", "Entregado"),
                            ("failed", "Fallido"),
                            ("no_recipient", "Sin destinatario"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("download_url", models.URLField(blank=True, max_length=1000)),
                ("provider_message_id", models.CharField(blank=True, max_length=160)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "design",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="designs.design",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="design_deliveries_requested",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="designs.designversion",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
    ]
