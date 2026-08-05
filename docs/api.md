# API inicial

Base URL: `/api/v1/`

- `GET /health/` — comprueba disponibilidad del servicio.
- `GET|POST /branding/` — guías de marca.
- `GET|POST /products/` — catálogo de productos.
- `GET|POST /branches/` — sedes y contactos autorizados.
- `GET|POST /campaigns/` — campañas y promociones aprobadas.
- `GET|POST /briefs/` — briefs validados contra `contracts/design-brief.schema.json`.
- `GET|POST /designs/` — diseños y versiones.
- `GET|POST /assets/` — activos oficiales.
- `GET|POST /validations/` — ejecuciones de validación.

La autenticación corporativa y los permisos por rol quedan para la siguiente fase; el MVP deja la API abierta únicamente para facilitar integración local.
