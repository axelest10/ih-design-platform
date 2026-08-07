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
