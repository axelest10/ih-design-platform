# Propuesta: modelo genérico de tipos de material

Estado: diseño aprobado para la primera implementación. `materials/` contiene el modelo inicial de
`MaterialType`, `MaterialTemplate`, `MaterialBundle` y `MaterialBundleItem`; `school-kit-v1` fue
sembrado por migración y ya puede generar piezas HTML/SVG por producto. Las extensiones futuras
siguen siendo propuesta.

## Objetivo

Extender el pipeline actual:

```text
DesignBrief → Design → DesignVersion → renderer → revisión
```

para que soporte piezas sociales, mailings y paquetes de marketing sin crear un pipeline nuevo
por cada área. `DesignBrief` seguirá siendo la unidad de solicitud y `Design` la unidad de una
pieza renderizable.

## Conceptos propuestos

### `MaterialType`

Catálogo técnico de tipos de material, separado de productos comerciales.

Campos propuestos:

- `slug`: identificador estable, por ejemplo `social-post`, `email`, `school-kit`, `branch-kit` o
  `sales-kit`.
- `name`: nombre visible.
- `renderer_family`: familia de renderizador, por ejemplo `html-svg`, `email-html` o `document`.
- `channel`: canal principal, por ejemplo `instagram`, `email`, `school` o `sales`.
- `active`: permite retirar un tipo sin borrar historial.
- `schema_version`: versión del contrato específico del material.

No debe contener colores, reglas de logo ni productos. Esos datos siguen en `brand/` y
`brand/knowledge/`.

### `MaterialTemplate`

Registro versionado de la plantilla que sabe renderizar un tipo.

Campos propuestos:

- `material_type`.
- `template_key` y `template_version`.
- `renderer_entrypoint` o familia de renderer.
- `dimensions` y `output_formats`.
- `required_fields` y `constraints` como JSON validado contra un esquema.
- `active`.

La plantilla no debe guardar reglas comerciales ni duplicar tokens de marca. El template lee
tokens autorizados y recibe datos validados desde el brief.

### `MaterialBundle`

Agrupador opcional para una paquetería con varias piezas. No reemplaza a `DesignBrief` ni a
`Design`.

Campos propuestos:

- `name`, `country`, `branch` y `campaign` cuando apliquen.
- `created_by`, `status` y timestamps.
- relación uno-a-muchos con briefs hijos.

Cada pieza del paquete conserva su propia versión, revisión y resultado de validación. Esto evita
que aprobar una pieza apruebe automáticamente todas las demás.

### `school-kit` implementado

Cada producto seleccionado genera tres briefs hijos y tres diseños independientes:

- `hero-square` → `square-v1`;
- `story-call-to-action` → `story-v1`;
- `portrait-information` → `portrait-v1`.

Además, cada paquete genera una sola carta formal (`letter-a4-v1`), un anuncio escolar
(`announcement-a4-v1`) y un flyer general (`flyer-a4-v1`). Estos documentos no se repiten por
producto porque comunican el paquete institucional completo. Pertenecen a `school-documents`,
usan el renderer PDF y también están disponibles individualmente en el editor rápido.

El endpoint `POST /api/v1/material-bundles/{id}/generate/` persiste el HTML y el SVG en la
`DesignVersion` y dispara `ai.services.run_automatic_design_review` para cada pieza. La revisión
usa exclusivamente `DesignVersion.claude_review_status` y `Design.claude-review`; no existe un
estado paralelo para los paquetes. Mientras Axel no confirme proveedor, API key y modelo de
Claude, el proveedor explícito `claude-stub` conserva el estado `pending` y registra
`integration_status=needs_confirmation` en `claude_review`. Un proveedor real puede inyectarse en
la misma interfaz y devolver `pass` o `needs_changes`. Cambridge, IELTS, MET, QC y
otros logos se conservan como logos secundarios mediante `additional_logo_keys`, no como productos
principales del brief. Los productos sin pilar/color confirmado quedan marcados como
`needs_confirmation` en la validación de la pieza.

## Encaje con el modelo actual

| Necesidad | Representación propuesta | Reutilización actual |
| --- | --- | --- |
| Post, historia o vertical social | `MaterialType` + `MaterialTemplate` | `DesignBrief.format`, `Design`, `DesignVersion`, renderer HTML/SVG |
| Mailing | `MaterialType=email` + template HTML responsive | brief, campaña, producto, tokens, revisión de versión |
| Paquetería para colegios | `MaterialBundle` + briefs hijos de tipo `school-kit` | catálogo, logos por país, referencias visuales y revisiones por pieza |
| Paquetería para sedes | `MaterialBundle` + briefs hijos de tipo `branch-kit` | `Branch`, logos regionales, campañas y assets oficiales |
| Paquetería para ventas | `MaterialBundle` + briefs hijos de tipo `sales-kit` | producto, campaña, CTA autorizado, referencias y versiones |

El campo `format` actual debe mantenerse temporalmente para compatibilidad. Los formatos sociales
existentes se mapearían así:

- `square` → `social-post` + template `square-v1`.
- `story` → `social-post` + template vertical story.
- `portrait` → `social-post` + template vertical portrait.
- `reel`, `carousel` y `banner` → tipos o templates explícitos cuando exista un renderer real;
  no deben considerarse implementados solo porque el enum ya los acepta.

## Cambios de datos previstos

### `DesignBrief`

- agregar `material_type` como FK nullable durante la transición;
- agregar `material_template` opcional o resolverlo por reglas de selección;
- conservar `format` mientras existan clientes legacy;
- agregar `bundle` nullable si la pieza pertenece a una paquetería;
- mantener `brief_data` para campos específicos, pero validarlo contra el esquema de la plantilla;
- no duplicar `product`, `branch`, `campaign`, logos ni colores fuera de sus relaciones/contratos
  autorizados.

### `Design`

- derivar el tipo desde el brief y opcionalmente guardar una FK para consultas rápidas;
- conservar exactamente un `Design` por brief;
- mantener los estados actuales, incluida la revisión de Claude y el lote de pruebas.

### `DesignVersion`

- conservar el versionado inmutable;
- agregar, si se necesita, `output_manifest` para indicar archivos producidos, MIME types y
  dimensiones;
- conservar `render_data`, `asset_refs`, `validation_summary` y `claude_review`.

### `ValidationRun`

- agregar el nombre de la regla, severidad, coordenadas y evidencia cuando se implemente la
  verificación de zona segura/legibilidad;
- no mezclar resultados de revisión visual de Claude con validaciones deterministas del renderer.

## Migraciones previstas

1. Crear `MaterialType`, `MaterialTemplate` y, si se aprueba el concepto de paquetes, `MaterialBundle`.
2. Insertar tipos y templates iniciales con una migración de datos explícita.
3. Agregar FKs nullable a `DesignBrief` y mapear los formatos actuales sin cambiar historiales.
4. Hacer que serializers y endpoints acepten el nuevo contrato manteniendo el payload legacy.
5. Migrar el renderer a resolver `material_type + template_version`.
6. Cuando exista cobertura suficiente, marcar `format` como legacy; no eliminarlo hasta migrar
   clientes y datos existentes.

Cada migración debe incluir pruebas de reversibilidad lógica, no borrar versiones ni reescribir
`DesignVersion` existentes.

## Qué se reutiliza de `brand/` sin cambios

- tokens YAML y sus artefactos generados;
- colores autorizados por producto/pilar;
- manifest de logos y restricciones por país/rol;
- tipografía documentada y fallback sin redistribuir Aptos sin licencia;
- reglas de logo, contraste y espaciado con su procedencia;
- assets oficiales y variantes permitidas.

## Qué se reutiliza de `brand/knowledge/` sin cambios

- `product-catalog.yaml/json` para productos y alcance por país;
- `artwork-annotations.yaml` como capa curada separada de hechos técnicos;
- `artwork-reference-knowledge.json` como índice de selección de referencias;
- filtros por país, producto, formato, orientación, campaña y estado de revisión;
- procedencia, `needs_review` y guardrails: una referencia inspira, pero no convierte una regla
  individual en regla oficial.

## Decisiones que deben aprobarse antes de extender el catálogo genérico

- si una paquetería se modelará como `MaterialBundle` o solo como un conjunto de briefs relacionados;
- qué tipos de material iniciales entran en el primer catálogo;
- qué renderer corresponde a mailings y documentos;
- si el catálogo de templates vivirá en YAML/manifest o en tablas de base de datos;
- qué campos de cada paquete son obligatorios y quién puede aprobarlo.

## Fuera de este diseño

- no implementa generación de imágenes;
- no implementa un editor visual;
- no crea productos comerciales nuevos;
- la primera definición `school-kit` reutiliza todos los productos activos del catálogo y prioriza
  `qc-2026` y `teacher-training-certifications`, confirmado por Axel el 2026-08-08;
- no modifica los archivos generados de `brand/`; consume el catálogo y los colores autorizados
  mediante los loaders existentes.
