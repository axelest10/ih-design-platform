import hashlib
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.utils._os import safe_join

ASSET_ROOTS = {
    "styles": settings.BASE_DIR / "frontend" / "styles",
    "scripts": settings.BASE_DIR / "frontend" / "scripts",
    "brand/generated": settings.BASE_DIR / "brand" / "generated",
}


@lru_cache(maxsize=256)
def file_digest(path: str, modified_ns: int, size: int) -> str:
    """Return a short content hash; stat values invalidate the process-local cache."""
    del modified_ns, size
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def asset_version(asset_path: str) -> str:
    normalized = asset_path.lstrip("/")
    for prefix, root in ASSET_ROOTS.items():
        if normalized == prefix or normalized.startswith(f"{prefix}/"):
            relative_path = normalized.removeprefix(prefix).lstrip("/")
            absolute_path = Path(safe_join(root, relative_path))
            stat = absolute_path.stat()
            return file_digest(str(absolute_path), stat.st_mtime_ns, stat.st_size)
    raise ValueError(f"Ruta de asset no versionable: {asset_path}")


def versioned_asset_url(asset_path: str) -> str:
    normalized = asset_path.lstrip("/")
    return f"/{normalized}?v={asset_version(normalized)}"
