"""Adaptador REST de Cloudflare Workers AI para imágenes base sin copy ni logos."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from PIL import Image, UnidentifiedImageError

from .base import AIProviderError, GenerationRequest, GenerationResponse

CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
DEFAULT_CLOUDFLARE_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]
ArtifactStore = Callable[[bytes, str, str], str]
MULTIPART_BOUNDARY = "----ih-design-platform-cloudflare"


def _cloudflare_error(exc: HTTPError) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return None, None
    code = errors[0].get("code")
    message = errors[0].get("message")
    return (
        str(code) if isinstance(code, int | str) else None,
        message if isinstance(message, str) else None,
    )


def _multipart_body(payload: dict[str, Any]) -> tuple[bytes, str]:
    chunks = []
    for name, value in payload.items():
        chunks.extend(
            (
                f"--{MULTIPART_BOUNDARY}\r\n",
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n',
                f"{value}\r\n",
            )
        )
    chunks.append(f"--{MULTIPART_BOUNDARY}--\r\n")
    return (
        "".join(chunks).encode("utf-8"),
        f"multipart/form-data; boundary={MULTIPART_BOUNDARY}",
    )


def _default_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    body, content_type = _multipart_body(payload)
    request = Request(
        url,
        data=body,
        headers={**headers, "content-type": content_type},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS origin
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        code, message = _cloudflare_error(exc)
        detail = ": ".join(part for part in (code, message) if part)
        suffix = f" ({detail})" if detail else ""
        raise AIProviderError(
            f"Cloudflare Workers AI rechazó la generación con HTTP {exc.code}{suffix}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise AIProviderError(
            "Cloudflare Workers AI no respondió dentro del tiempo permitido."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AIProviderError(
            "Cloudflare Workers AI devolvió una respuesta no válida."
        ) from exc


def _default_artifact_store(image_bytes: bytes, mime_type: str, checksum: str) -> str:
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    extension = "jpg" if mime_type == "image/jpeg" else "png"
    storage_key = f"ai-generated/cloudflare/{checksum}.{extension}"
    if default_storage.exists(storage_key):
        return storage_key
    return default_storage.save(storage_key, ContentFile(image_bytes))


def _image_payload(response: dict[str, Any]) -> str:
    result = response.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and isinstance(result.get("image"), str):
        return result["image"]
    raise AIProviderError("Cloudflare Workers AI no devolvió una imagen Base64.")


def _decode_image(image_base64: str) -> tuple[bytes, str, int, int]:
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
            mime_type = Image.MIME.get(image.format or "")
    except (ValueError, UnidentifiedImageError, OSError) as exc:
        raise AIProviderError(
            "Cloudflare Workers AI devolvió una imagen no válida."
        ) from exc
    if mime_type not in {"image/png", "image/jpeg"}:
        raise AIProviderError("Cloudflare Workers AI devolvió un formato de imagen no permitido.")
    return image_bytes, mime_type, width, height


def _dimension(context: dict[str, Any], key: str) -> int:
    value = context.get(key, 1024)
    if not isinstance(value, int) or not 256 <= value <= 1920:
        raise AIProviderError(f"Cloudflare Workers AI requiere {key} entre 256 y 1920.")
    return value


class CloudflareWorkersAIProvider:
    name = "cloudflare-workers-ai"

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
        transport: Transport | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        self.account_id = (
            account_id
            if account_id is not None
            else getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
        )
        self.api_token = (
            api_token
            if api_token is not None
            else getattr(settings, "CLOUDFLARE_API_TOKEN", "")
        )
        self.model = model if model is not None else getattr(
            settings, "CLOUDFLARE_IMAGE_MODEL", DEFAULT_CLOUDFLARE_IMAGE_MODEL
        )
        self.timeout = timeout
        self.transport = transport or _default_transport
        self.artifact_store = artifact_store or _default_artifact_store

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.account_id or not self.api_token:
            raise AIProviderError(
                "Cloudflare Workers AI requiere CLOUDFLARE_ACCOUNT_ID y "
                "CLOUDFLARE_API_TOKEN."
            )
        width = _dimension(request.authorized_context, "width")
        height = _dimension(request.authorized_context, "height")
        context = json.dumps(request.authorized_context, ensure_ascii=False)
        payload = {
            "prompt": (
                f"{request.instruction}\n\n"
                "Genera una imagen base sin logos ni copy final. "
                f"CONTEXTO_AUTORIZADO_JSON: {context}"
            ),
            "width": width,
            "height": height,
        }
        model_path = quote(self.model, safe="@/")
        url = (
            f"{CLOUDFLARE_API_BASE_URL}/accounts/{quote(self.account_id, safe='')}"
            f"/ai/run/{model_path}"
        )
        headers = {
            "authorization": f"Bearer {self.api_token}",
        }
        try:
            response = self.transport(url, headers, payload, float(self.timeout))
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                "Cloudflare Workers AI falló antes de obtener una respuesta válida."
            ) from exc
        image_bytes, mime_type, actual_width, actual_height = _decode_image(
            _image_payload(response)
        )
        checksum = hashlib.sha256(image_bytes).hexdigest()
        artifact_ref = self.artifact_store(image_bytes, mime_type, checksum)
        descriptor = {
            "artifact_ref": artifact_ref,
            "mime_type": mime_type,
            "width": actual_width,
            "height": actual_height,
            "checksum": checksum,
        }
        result_info = response.get("result_info")
        return GenerationResponse(
            provider=self.name,
            model=self.model,
            content=json.dumps(descriptor, sort_keys=True),
            metadata={"result_info": result_info} if result_info is not None else {},
        )
