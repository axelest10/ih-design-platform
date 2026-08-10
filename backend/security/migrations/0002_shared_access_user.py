from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations

SHARED_ACCESS_USERNAME = "shared-access"
SHARED_ACCESS_EMAIL = "acceso@ihmexico.com"
CORPORATE_ROLES = (
    "platform_admin",
    "marketing",
    "designer",
    "reviewer",
    "viewer",
)


def create_shared_access_user(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    group_model = apps.get_model("auth", "Group")
    user, _ = user_model.objects.get_or_create(
        username=SHARED_ACCESS_USERNAME,
        defaults={"email": SHARED_ACCESS_EMAIL},
    )
    user.email = SHARED_ACCESS_EMAIL
    user.password = make_password(None)
    user.is_active = True
    user.save(update_fields=["email", "password", "is_active"])

    groups = [group_model.objects.get_or_create(name=role)[0] for role in CORPORATE_ROLES]
    user.groups.add(*groups)


def remove_shared_access_user(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    user_model.objects.filter(username=SHARED_ACCESS_USERNAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("security", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_shared_access_user, remove_shared_access_user),
        migrations.DeleteModel(name="MagicLinkToken"),
    ]
