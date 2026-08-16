from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("briefs", "0005_alter_briefreferenceupload_file"),
    ]

    operations = [
        migrations.AlterField(
            model_name="designbrief",
            name="format",
            field=models.CharField(
                choices=[
                    ("square", "Post cuadrado"),
                    ("story", "Historia"),
                    ("portrait", "Post vertical"),
                    ("reel", "Reel"),
                    ("carousel", "Carrusel"),
                    ("banner", "Banner"),
                    ("presentation", "Presentación"),
                    ("html", "HTML"),
                    ("svg", "SVG"),
                ],
                max_length=16,
            ),
        ),
    ]
