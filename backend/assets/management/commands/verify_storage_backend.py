"""Verifica escritura, lectura y borrado contra el bucket R2 de staging."""
from __future__ import annotations

from urllib.parse import urlparse
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verifica que el storage S3-compatible de staging pueda escribir y leer en R2."

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            default="",
            help="Clave exacta del objeto de prueba; por defecto usa una clave temporal única.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Conserva el objeto después de verificarlo para inspección manual.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida configuración R2 sin ejecutar una escritura de red.",
        )

    def handle(self, *args, **options):
        endpoint_host = self._require_r2_configuration()
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        self.stdout.write(f"storage_backend={settings.STORAGES['default']['BACKEND']}")
        self.stdout.write(f"endpoint_host={endpoint_host}")
        self.stdout.write(f"bucket_configured={'yes' if bucket else 'no'}")
        if options["dry_run"]:
            self.stdout.write("result=configuration_ready")
            return

        key = options["key"].strip() or f"operations/r2-write-verification/{uuid4()}.txt"
        content = f"ih-design-platform R2 verification {uuid4()}\n".encode()
        saved_key = None
        try:
            saved_key = default_storage.save(key, ContentFile(content))
            if not default_storage.exists(saved_key):
                raise CommandError(f"El objeto no aparece después de guardar: {saved_key}")
            with default_storage.open(saved_key, "rb") as handle:
                read_back = handle.read()
            if read_back != content:
                raise CommandError("El contenido leído no coincide con el contenido escrito.")
            self.stdout.write("write=passed")
            self.stdout.write("read=passed")
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                "La escritura/lectura contra R2 falló; revisa endpoint, bucket y credenciales."
            ) from exc
        finally:
            if saved_key and not options["keep"]:
                try:
                    default_storage.delete(saved_key)
                except Exception as exc:
                    raise CommandError(
                        "La prueba leyó correctamente, pero no pudo borrar el objeto temporal."
                    ) from exc
                self.stdout.write("delete=passed")
        self.stdout.write(f"verified_key={saved_key}")
        self.stdout.write("result=passed")

    @staticmethod
    def _require_r2_configuration() -> str:
        backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
        if backend != "storages.backends.s3.S3Storage":
            raise CommandError(
                "R2 storage no está activo: configura AWS_STORAGE_BUCKET_NAME para usar "
                "storages.backends.s3.S3Storage."
            )
        bucket = str(getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or "").strip()
        endpoint = str(getattr(settings, "AWS_S3_ENDPOINT_URL", "") or "").strip()
        host = urlparse(endpoint).hostname or ""
        if not bucket or not host.endswith(".r2.cloudflarestorage.com"):
            raise CommandError(
                "R2 no está configurado: AWS_STORAGE_BUCKET_NAME y "
                "AWS_S3_ENDPOINT_URL=<account>.r2.cloudflarestorage.com son obligatorios."
            )
        return host
