from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError

from assets.models import ArtworkReference


class Command(BaseCommand):
    help = (
        "Sincroniza brand/assets/artwork-references/manifest.yaml "
        "con la biblioteca de referencias."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            type=Path,
            default=Path("brand/assets/artwork-references/manifest.yaml"),
        )

    def handle(self, *args, **options):
        manifest_path = options["manifest"]
        if not manifest_path.exists():
            raise CommandError(f"No existe el manifest: {manifest_path}")

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        entries = manifest.get("entries", [])
        created = 0
        updated = 0

        for entry in entries:
            defaults = {
                "title": entry["title"],
                "reference_type": entry.get("reference_type", "inspiration"),
                "source_url": entry.get("source_url", ""),
                "source_folder_url": entry.get("source_folder_url", ""),
                "source_file_name": entry.get("source_file_name", ""),
                "repository_path": entry.get(
                    "file", entry.get("repository_path", "")
                ),
                "brand_scope": entry.get("brand_scope", "international-house-latam"),
                "country": entry.get("country", ""),
                "product_slug": entry.get("product_slug", ""),
                "format": entry.get("format", ""),
                "tags": entry.get("tags", []),
                "usage_notes": entry.get("usage_notes", ""),
                "provenance": entry.get("provenance", {}),
            }
            reference, was_created = ArtworkReference.objects.get_or_create(
                key=entry["key"],
                defaults={
                    **defaults,
                    "approval_status": entry.get("approval_status", "pending"),
                },
            )
            if was_created:
                created += 1
                continue

            for field, value in defaults.items():
                setattr(reference, field, value)
            reference.save(update_fields=[*defaults, "updated_at"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Artwork references sincronizadas: {created} creadas, {updated} actualizadas."
            )
        )
