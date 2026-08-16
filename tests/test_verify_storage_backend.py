from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


def test_verify_storage_backend_dry_run_reports_ready_configuration(capsys):
    with override_settings(
        AWS_STORAGE_BUCKET_NAME="ih-staging",
        AWS_S3_ENDPOINT_URL="https://account.r2.cloudflarestorage.com",
        STORAGES={
            "default": {"BACKEND": "storages.backends.s3.S3Storage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    ):
        call_command("verify_storage_backend", "--dry-run")

    output = capsys.readouterr().out
    assert "endpoint_host=account.r2.cloudflarestorage.com" in output
    assert "result=configuration_ready" in output


def test_verify_storage_backend_fails_without_r2_configuration():
    with override_settings(
        AWS_STORAGE_BUCKET_NAME="",
        AWS_S3_ENDPOINT_URL="",
        STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}},
    ):
        with pytest.raises(CommandError, match="R2 storage no está activo"):
            call_command("verify_storage_backend", "--dry-run")


def test_verify_storage_backend_writes_reads_and_deletes_object():
    class FakeStorage:
        def __init__(self):
            self.objects = {}

        def save(self, key, content):
            self.objects[key] = content.read()
            return key

        def exists(self, key):
            return key in self.objects

        def open(self, key, mode):
            return BytesIO(self.objects[key])

        def delete(self, key):
            del self.objects[key]

    storage = FakeStorage()
    with (
        override_settings(
            AWS_STORAGE_BUCKET_NAME="ih-staging",
            AWS_S3_ENDPOINT_URL="https://account.r2.cloudflarestorage.com",
            STORAGES={
                "default": {"BACKEND": "storages.backends.s3.S3Storage"},
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
                },
            },
        ),
        patch(
            "assets.management.commands.verify_storage_backend.default_storage", storage
        ),
    ):
        call_command("verify_storage_backend", "--key", "tests/r2-check.txt")

    assert storage.objects == {}
