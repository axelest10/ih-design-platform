# Testing

## Checks actuales

El CI ejecuta:

```text
ruff check .
python brand/scripts/generate_tokens.py --check
python brand/scripts/generate_product_catalog.py --check
python brand/scripts/build_design_knowledge.py ... + comparación del JSON generado
python manage.py check
pytest
```

El estado local verificado el 2026-08-07 es 95 pruebas pasando y sin cambios de migración
pendientes.

## Cobertura funcional existente

- tokens y colores por producto;
- catálogo y conocimiento visual;
- permisos corporativos y roles;
- carga de logos y referencias;
- renderer square, story y portrait;
- zona segura, layout de texto, contraste y dual-branding;
- flujo de preview y revisión de Claude.

## Pendientes no inventados

No existe todavía un checklist formal de accesibilidad/móvil, pruebas de concurrencia, prueba contra
un PostgreSQL desplegado ni smoke tests contra un proveedor de hosting. Deben agregarse cuando exista
el entorno correspondiente.

## Lote reproducible de 50 diseños

`scripts/design_validation_batch.py` define 50 casos sintéticos que cubren los cinco productos
principales, México/Colombia/Perú/Chile, square/story/portrait, dos idiomas, distintos tonos, CTAs,
longitudes de copy y casos con/sin logo adicional.

El modo predeterminado no usa red:

```text
python scripts/design_validation_batch.py
```

La ejecución real requiere una cuenta autorizada en variables de entorno y una confirmación
explícita mediante `--execute`:

```text
IH_DESIGN_USERNAME=<usuario> IH_DESIGN_PASSWORD=<secreto> \
python scripts/design_validation_batch.py --execute
```

Antes de crear registros, el script confirma que `DESIGN_TEST_MODE` está activo, que
`DESIGN_TEST_LIMIT` sigue siendo 50, consulta briefs/diseños existentes y solo ocupa los espacios
restantes. Es reanudable por el título sintético de cada caso y nunca aprueba ni elimina piezas.
Cada diseño puede consumir como máximo tres llamadas de proveedor: copy inicial, estructuración y
revisión visual. El techo completo es 150 llamadas. El reporte se guarda por defecto en
`docs/testing/design-validation-batch-report.json`; no incluye credenciales.
