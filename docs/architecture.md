# Arquitectura

```text
Cliente futuro
     |
     v
Django REST API ---- briefs ---- catálogo/campañas/sedes
     |                    |
     |                    v
     +---- diseños/versiones ---- validaciones ---- activos oficiales
     |
     +---- AIProvider ---- OpenAI (inicial)
     |
     +---- branding.services ---- brand/ (tokens, colores por producto, activos, docs)
     |
 PostgreSQL + pgvector (preparado) / Redis + Celery / S3
```

El backend organiza el dominio en aplicaciones Django independientes. Los briefs apuntan a entidades autorizadas y los diseños conservan versiones inmutables por número. El renderizado aún no está implementado: el campo `render_data` es el contrato de entrada para la futura capa HTML/SVG.

## Sistema de marca (`brand/` + `branding.services`)

`brand/` (raíz del repositorio, fuera de `backend/`) es la dependencia de marca reutilizable:
YAML fuente en `brand/tokens/` y `brand/product-colors/`, activos oficiales en `brand/assets/`,
reglas en `brand/documentation/`, y artefactos generados (CSS/JS/Tailwind) en `brand/generated/`
— nunca editados a mano, siempre regenerados con `brand/scripts/generate_tokens.py`.

El backend no lee `brand/` directamente desde `catalog`, `campaigns`, `briefs`, `designs` ni
`assets` — toda lectura pasa por `backend/branding/services/`:

- `loader.py` — carga y cachea (`functools.cache`) los YAML de `brand/` como diccionarios
  Python; `clear_cache()` se usa en tests para invalidar el cache entre casos.
- `validators.py` — valida formato HEX, si un color pertenece a la paleta institucional, si un
  color corresponde al pilar/producto correcto, y si un logo está registrado y aprobado en
  `brand/assets/logos/manifest.yaml`. También expone `find_duplicate_token_conflicts()` para
  detectar contradicciones entre `brand/tokens/colors.yaml` y
  `brand/product-colors/authorized-colors.yaml`.

El modelo existente `branding.BrandGuideline` (base de datos) se mantiene como la
representación consultable vía el CRUD estándar (`/api/v1/branding/`), pero su contenido se
sincroniza *desde* `brand/` con el management command `sync_brand_guideline` — los archivos
son la fuente de verdad, no la base de datos.

Endpoints adicionales, de solo lectura, expuestos directamente sobre los archivos:

- `GET /api/v1/branding/tokens/` — el árbol completo de tokens (colores, tipografía, espaciado,
  radios, sombras, motion, colores por producto).
- `GET /api/v1/branding/validate-color/?hex=#3B44B5&pillar=cambridge` — valida un color contra
  la paleta institucional o, si se pasa `pillar`, contra los colores autorizados de ese pilar.

## Persistencia y procesos

- PostgreSQL es la base recomendada; las migraciones evitan acoplar el dominio a SQLite.
- `backend/config/celery.py` registra Celery con Redis como broker futuro.
- S3 se activa si existe `AWS_STORAGE_BUCKET_NAME`; el modelo de activos conserva checksum y reglas de uso.
- pgvector queda preparado a nivel de infraestructura/documentación, sin imponer todavía embeddings ni costos operativos.

## Seguridad de contenido

La información comercial autorizada es la fuente de verdad. El adaptador IA recibe `authorized_context` y aplica instrucciones de seguridad, pero las validaciones de campos críticos y la composición final deben ejecutarse en una plantilla controlada.
