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
- `POST /auth/login/` — autentica un usuario individual con contraseña Django y limita intentos
  por IP; el error no distingue entre usuario y contraseña incorrectos.
- `POST /auth/change-password/` — permite que una persona autenticada cambie su propia contraseña
  verificando la actual; conserva la sesión activa después del cambio.
- `GET|POST /security/users/` — lista o crea usuarios corporativos (`platform_admin`).
- `POST /security/users/{id}/password/` — establece una contraseña nueva (`platform_admin`).
- `GET /material-types/` — tipos de material activos; `school-kit` expone todos los productos
  activos del catálogo, prioriza `qc-2026` y `teacher-training-certifications` y declara seis
  entregables: tres sociales por producto y tres documentos formales por paquete.
- `GET|POST /material-bundles/` — paquetes de materiales con productos del catálogo y briefs hijos;
  crear requiere `platform_admin`, `marketing` o `designer`.
- `PATCH /material-bundles/{id}/` — edita un paquete antes de generar sus piezas.
- `POST /material-bundles/{id}/generate/` — crea tres piezas HTML/SVG por producto y una carta,
  un anuncio y un flyer PDF por paquete; cada pieza conserva su propio brief, design, versión y
  revisión visual mediante `ai.services`. Hasta
  confirmar la integración real con Claude, el stub conserva `pending` y registra
  `integration_status=needs_confirmation` dentro de `claude_review`.
- `GET /material-templates/` — templates versionados asociados a un tipo de material.
- `POST /materials/quick-design/` — crea `DesignBrief`, `Design` y `DesignVersion` desde una
  plantilla activa y sus campos editables; devuelve el preview HTML/SVG o la URL del PDF/PPTX.
- `GET /marketing-assets/` — biblioteca pública de materiales descargables; filtra por `brand`,
  `country` y `category`, y solo expone entradas activas a perfiles no administradores.
- `POST|PATCH|DELETE /marketing-assets/` — administración y carga multipart restringida a
  `platform_admin`; el archivo usa el storage configurado (local o S3-compatible).
- `POST /materials/marketing-assets/bulk/` — carga hasta 30 archivos con marca, país y categoría
  compartidos; informa por separado los creados y los fallidos (`platform_admin`).
- `POST /artwork-references/{id}/approve/` — aprueba una referencia como reviewer/admin.
- `POST /artwork-references/{id}/reject/` — rechaza una referencia como reviewer/admin.
- `GET|POST /validations/` — ejecuciones de validación.

Cuando `DJANGO_REQUIRE_CORPORATE_AUTH=1`, todos los endpoints salvo `/health/`, el acceso interno
y el catálogo público de marca requieren sesión corporativa y dominio autorizado. La configuración
del acceso y de los roles está en
`docs/security.md`.
