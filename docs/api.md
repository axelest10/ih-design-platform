# API inicial

Base URL: `/api/v1/`

El modo inicial de pruebas se controla con `DESIGN_TEST_MODE=1` y `DESIGN_TEST_LIMIT=50`.
Durante ese lote, la revisiÃ³n de Claude mueve el diseÃ±o a `test_ready` o
`revision_requested`; la aprobaciÃ³n humana permanece deshabilitada para briefs de producto
hasta desactivar el modo.

- `GET /health/` — comprueba disponibilidad del servicio (público).
- `GET|POST /branding/` — guías de marca.
- `GET /branding/tokens/` — tokens completos de marca.
- `GET /branding/logos/` — catálogo LATAM de logos aprobados; filtra por `scope`, `country`,
  `brand` y `variant`.
- `GET|POST /products/` — catálogo de productos.
- `GET|POST /branches/` — sedes y contactos autorizados.
- `GET|POST /campaigns/` — campañas y promociones aprobadas.
- `GET|POST /briefs/` — briefs validados contra `contracts/design-brief.schema.json`.
- `GET /briefs/options/` — países, los cinco productos principales, colores autorizados y
  logos permitidos según el país y rol.
- `POST /uploaded-logos/` — carga un logo aportado por el usuario como `pending_catalog`, sin
  modificar el catálogo oficial.
- `POST /brief-reference-uploads/` — adjunta una referencia visual a un brief.
- `GET|POST /designs/` — diseños y versiones.
- `POST /designs/{id}/preview/` — genera HTML/SVG con `square-v1`, `story-v1` o `portrait-v1`,
  crea una versión y pasa el diseño al estado correspondiente al modo de pruebas.
- `POST /designs/{id}/claude-review/` — registra `pass|needs_changes` y mueve el diseño a
  `test_ready` o `revision_requested`; no es aprobación humana.
- `POST /designs/{id}/review/` — aprueba o rechaza una versión (`decision: approve|reject`).
- `GET|POST /assets/` — activos oficiales.
- `GET|POST /artwork-references/` — biblioteca de bases aprobadas e inspiración; filtra por
  `reference_type`, `approval_status`, `country`, `brand_scope` y `format`. Las entradas
  sincronizadas desde Drive conservan `source_url`, `source_folder_url` y `repository_path`.
- `GET /artwork-references/knowledge/` — base JSON técnica para selección precisa; admite
  `country`, `media_type`, `format`, `orientation`, `tag` y `limit`.
- `GET /me/` — perfil, roles, paneles disponibles y acceso regional del usuario actual.
- `GET /material-types/` — tipos de material activos; `school-kit` expone todos los productos
  activos del catálogo, prioriza `qc-2026` y `teacher-training-certifications` y declara tres
  entregables iniciales (`square-v1`, `story-v1`, `portrait-v1`).
- `GET|POST /material-bundles/` — paquetes de materiales con productos del catálogo y briefs hijos;
  crear requiere `platform_admin`, `marketing` o `designer`.
- `PATCH /material-bundles/{id}/` — edita un paquete antes de generar sus piezas.
- `POST /material-bundles/{id}/generate/` — crea un brief, un design y una DesignVersion HTML/SVG
  por combinación producto/entregable y dispara su revisión visual mediante `ai.services`. Hasta
  confirmar la integración real con Claude, el stub conserva `pending` y registra
  `integration_status=needs_confirmation` dentro de `claude_review`.
- `GET /material-templates/` — templates versionados asociados a un tipo de material.
- `POST /artwork-references/{id}/approve/` — aprueba una referencia como reviewer/admin.
- `POST /artwork-references/{id}/reject/` — rechaza una referencia como reviewer/admin.
- `GET|POST /validations/` — ejecuciones de validación.

Cuando `DJANGO_REQUIRE_CORPORATE_AUTH=1`, todos los endpoints salvo `/health/` requieren sesión
corporativa y dominio autorizado. La configuración de dominios y roles está en
`docs/security.md`.
