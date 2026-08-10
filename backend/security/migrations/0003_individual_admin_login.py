from django.conf import settings
from django.db import migrations

SHARED_ACCESS_USERNAME = "shared-access"
INITIAL_ADMIN_USERNAME = "axel.estrada@ihmexico.com"
INITIAL_ADMIN_EMAIL = "axel.estrada@ihmexico.com"
INITIAL_ADMIN_PASSWORD_HASH = (
    "pbkdf2_sha256$1000000$hFCKzCnRTAQLFA1CwmJZFM$"
    "QQE1x8u/a/nIwVII/PjYP5dl6cDzVd9Nr8wWsc8pTYw="
)


def enable_individual_admin_login(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    group_model = apps.get_model("auth", "Group")
    user_model.objects.filter(username=SHARED_ACCESS_USERNAME).update(is_active=False)

    admin, _ = user_model.objects.update_or_create(
        username=INITIAL_ADMIN_USERNAME,
        defaults={
            "email": INITIAL_ADMIN_EMAIL,
            "password": INITIAL_ADMIN_PASSWORD_HASH,
            "is_active": True,
        },
    )
    platform_admin, _ = group_model.objects.get_or_create(name="platform_admin")
    admin.groups.add(platform_admin)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("security", "0002_shared_access_user"),
    ]

    operations = [migrations.RunPython(enable_individual_admin_login, migrations.RunPython.noop)]
