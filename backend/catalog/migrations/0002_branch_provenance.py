from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="country",
            field=models.CharField(blank=True, max_length=8),
        ),
        migrations.AddField(
            model_name="branch",
            name="source_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
