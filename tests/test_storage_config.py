"""Pruebas de selección de storage (local vs S3-compatible via django-storages).

Recarga `config.settings` como módulo aislado bajo variables de entorno controladas
para verificar la lógica condicional sin afectar la configuración real de Django ya
cargada para el resto de la suite.
"""
from __future__ import annotations

import importlib
import sys

import pytest
from django.core.files.storage import default_storage

_S3_ENV_KEYS = (
    "AWS_STORAGE_BUCKET_NAME",
    "AWS_S3_REGION_NAME",
    "AWS_S3_ENDPOINT_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)


def _reload_settings_module(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]):
    """Reimporta config.settings bajo un entorno controlado sin tocar django.conf.settings."""
    for key in _S3_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    original_module = sys.modules.pop("config.settings", None)
    try:
        return importlib.import_module("config.settings")
    finally:
        sys.modules.pop("config.settings", None)
        if original_module is not None:
            sys.modules["config.settings"] = original_module


def test_default_storage_is_local_filesystem_without_s3_variables():
    """Comportamiento actual (sin variables de S3): Django sigue usando el disco local."""
    # `default_storage` es un LazyObject; `type()` devuelve el wrapper (`DefaultStorage`), no la
    # clase real. `.__class__` sí resuelve al backend real vía la propiedad de LazyObject.
    assert "FileSystemStorage" in default_storage.__class__.__name__


def test_settings_module_has_no_s3_storage_without_bucket_variable(monkeypatch):
    module = _reload_settings_module(monkeypatch, {})
    assert module.AWS_STORAGE_BUCKET_NAME == ""
    assert not hasattr(module, "STORAGES")


def test_settings_module_selects_s3_storage_when_bucket_variable_is_set(monkeypatch):
    module = _reload_settings_module(
        monkeypatch,
        {
            "AWS_STORAGE_BUCKET_NAME": "dummy-test-bucket",
            "AWS_S3_REGION_NAME": "us-east-1",
            "AWS_S3_ENDPOINT_URL": "",
            "AWS_ACCESS_KEY_ID": "dummy-access-key",
            "AWS_SECRET_ACCESS_KEY": "dummy-secret-key",
        },
    )
    assert module.AWS_STORAGE_BUCKET_NAME == "dummy-test-bucket"
    assert module.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
    assert module.AWS_S3_REGION_NAME == "us-east-1"
    # Endpoint vacío => AWS S3 real (boto3 resuelve el endpoint por región).
    assert module.AWS_S3_ENDPOINT_URL is None
    assert module.AWS_ACCESS_KEY_ID == "dummy-access-key"
    assert module.AWS_SECRET_ACCESS_KEY == "dummy-secret-key"


def test_settings_module_supports_s3_compatible_endpoint(monkeypatch):
    """Un AWS_S3_ENDPOINT_URL con valor apunta a un proveedor S3-compatible (Backblaze, DO)."""
    module = _reload_settings_module(
        monkeypatch,
        {
            "AWS_STORAGE_BUCKET_NAME": "dummy-test-bucket",
            "AWS_S3_REGION_NAME": "us-west-000",
            "AWS_S3_ENDPOINT_URL": "https://s3.dummy-compatible-provider.example.com",
            "AWS_ACCESS_KEY_ID": "dummy-access-key",
            "AWS_SECRET_ACCESS_KEY": "dummy-secret-key",
        },
    )
    assert module.AWS_S3_ENDPOINT_URL == "https://s3.dummy-compatible-provider.example.com"
    assert module.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
