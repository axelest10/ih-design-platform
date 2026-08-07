"""Crea los grupos corporativos que el proveedor SSO deberá sincronizar."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from security.permissions import (
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ROLE_VIEWER,
)

ROLE_DESCRIPTIONS = {
    ROLE_PLATFORM_ADMIN: "Administra configuración y permisos de la plataforma.",
    ROLE_MARKETING: "Gestiona catálogo comercial, campañas, briefs y diseños.",
    ROLE_DESIGNER: "Crea briefs, diseños, previews y validaciones.",
    ROLE_REVIEWER: "Ejecuta validaciones y aprueba o rechaza diseños.",
    ROLE_VIEWER: "Consulta información autorizada sin editarla.",
}


class Command(BaseCommand):
    help = "Crea o actualiza los grupos corporativos esperados por la plataforma."

    def handle(self, *args, **options):
        for role_name, description in ROLE_DESCRIPTIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)
            action = "creado" if created else "existente"
            self.stdout.write(f"Rol '{group.name}': {action}. {description}")
