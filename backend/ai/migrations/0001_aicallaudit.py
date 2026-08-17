from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("briefs", "0005_alter_briefreferenceupload_file"),
        ("designs", "0004_asyncgenerationjob"),
        ("materials", "0013_email_kit"),
    ]
    operations = [
        migrations.CreateModel(
            name="AICallAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=80)),
                ("model", models.CharField(blank=True, max_length=160)),
                ("prompt", models.TextField()),
                ("response", models.TextField(blank=True)),
                ("request_context", models.JSONField(default=dict)),
                ("response_metadata", models.JSONField(default=dict)),
                ("quality_report", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("completed", "Completada"), ("error", "Error")], default="completed", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("brief", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_call_audits", to="briefs.designbrief")),
                ("design_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_call_audits", to="designs.designversion")),
                ("material_bundle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_call_audits", to="materials.materialbundle")),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
    ]
