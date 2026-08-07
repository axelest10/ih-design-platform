# brand/knowledge/ — catálogo de productos y base de conocimiento visual

Este directorio tiene dos sistemas relacionados pero independientes:

## 1. Catálogo de productos por país

- `product-catalog.yaml` — **fuente de verdad**, editable a mano. 15 productos: 6 pilares
  institucionales (confirmados para México, inferidos para el resto de LATAM por ser líneas de
  negocio estándar de la red IH), 1 sub-marca infantil (Hello Live Kids), 1 sub-marca sin pilar
  claro (QC), 1 producto descubierto por inspección visual (certificaciones docentes) y 6 marcas
  partner/certificadoras (Cambridge, IELTS, Michigan, TEA — Test of English for Aviation, esta
  última también descubierta por inspección visual). El grupo regional "IELTS LATAM" quedó
  deprecado (`superseded_by: ielts-preparation`) tras confirmación del cliente 2026-08-06.
- `product-catalog.json` — **generado**, no editar a mano. Se regenera con:
  ```bash
  python brand/scripts/generate_product_catalog.py          # regenera
  python brand/scripts/generate_product_catalog.py --check  # falla si quedó desactualizado
  ```

Cada producto documenta su fuente exacta (`source`), su estado (`confirmed` / `inferred` /
`needs_confirmation` / `deprecated`) y notas explícitas cuando algo no se pudo confirmar. Ver
`brand/knowledge/product-catalog.yaml` para el detalle completo y las preguntas abiertas.

## 2. Base de conocimiento visual (454 referencias)

Tres archivos separados, cada uno con una responsabilidad distinta:

- `brand/assets/artwork-references/manifest.yaml` (fuera de este directorio) — **hechos
  técnicos crawleados de Drive**: nombre de archivo, país, ruta, checksum, enlaces. No contiene
  ningún juicio semántico.
- `artwork-annotations.yaml` — **fuente de verdad de anotaciones semánticas**, editable a mano
  (o por un pase de anotación asistido). Tiene tres capas que se aplican en orden: un
  `default_annotation` (aplicado a los 454 assets), `heuristic_rules` (reglas declarativas que
  se aplican cuando coinciden, p. ej. orientación → `layout_pattern`, o palabra "ielts" en
  título/carpeta → `content_pillar`), y `overrides` por `id` de asset (máxima prioridad — se usa
  para los assets con revisión visual humana real).
- `artwork-reference-knowledge.json` — **generado**, no editar a mano. Combina el manifest + las
  anotaciones. Se regenera con:
  ```bash
  python brand/scripts/build_design_knowledge.py \
    brand/assets/artwork-references/manifest.yaml \
    brand/knowledge/artwork-reference-knowledge.json
  ```
  (usa `brand/knowledge/artwork-annotations.yaml` por defecto; se puede apuntar a otro archivo
  con `--annotations`).

`artwork-annotation-schema.json` documenta el vocabulario controlado completo de todos los
campos de anotación (composition_type, layout_pattern, background_type, logo_placement,
funnel_stage, annotation_status, etc.) — léelo antes de escribir nuevas anotaciones u
overrides.

### Estado de cobertura de anotación (2026-08-06, actualizado tras segunda pasada)

- **454/454** assets tienen todos los campos nuevos poblados con valores por defecto o
  heurísticos (cobertura completa, pero conservadora).
- **40/454** (8 por país + 8 del grupo IELTS LATAM, tras dos pasadas de revisión el mismo día)
  tienen revisión visual humana real (`annotation_status: human-reviewed`,
  `annotation_confidence: high/medium/low`) — sigue siendo una muestra de calibración ampliada,
  no cobertura total.
- **414/454** quedan con `needs_review: true` (incluye los 140 videos, que no tienen forma de
  analizarse visualmente sin descargar el binario desde Drive, y ~275 imágenes aún no revisadas
  individualmente). Nota: 5 de los 40 assets human-reviewed también quedan con
  `needs_review: true` de forma intencional, por ambigüedad genuina detectada en la revisión
  (ver `review_note` en cada uno): mexico/6-nov4 y colombia/6-nov4 (posible QC vs. Cambridge/
  teacher-training), colombia/21-feb2 (calendario multi-examen, posible IELTS + TEA), mexico/
  12-ene3 (campaña de cursos en línea sin pilar claro) y peru/1feb1 (University Programmes vs.
  teacher-training-certifications).

Durante la segunda pasada se descubrió por inspección visual directa un partner/certificación no
catalogado previamente: **TEA — Test of English for Aviation** (colombia/21-feb2 y
colombia/16-ene1), agregado a `product-catalog.yaml` como `tea-test-of-english-for-aviation`
(`brand_scope: partner`, `status: inferred`).

Para ampliar la cobertura de revisión humana: añadir más entradas a `overrides:` en
`artwork-annotations.yaml` (siguiendo el mismo formato que las 40 existentes) y volver a correr
`build_design_knowledge.py`. Las heurísticas (`heuristic_rules`) son el lugar para reglas que
apliquen a muchos assets a la vez sin revisión pieza por pieza (usar con criterio — solo para
señales muy confiables, como país o proporción de imagen).

### Guardrails (se mantienen sin importar cuántas anotaciones se agreguen)

- Ninguna anotación cambia `review.approval_status` automáticamente.
- `review.reuse_permission: client-authorized-reuse` refleja la autorización general del cliente
  (2026-08-06) para reutilizar/tomar como referencia toda la biblioteca — no es una aprobación
  de diseño específica pieza por pieza.
- Los colores en `technical.observed_palette` son metadata de imagen, no tokens oficiales de
  marca.
- Un `product_slug` en un asset individual nunca se trata como una regla oficial de marca.

## Endpoint

`GET /api/v1/artwork-references/knowledge/` acepta los filtros documentados en
`artwork-annotation-schema.json#endpoint_filters` — ver `backend/assets/views.py`.
