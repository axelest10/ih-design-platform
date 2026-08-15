# Diseño e implementación de `venue-kit`

**Estado:** implementado en `feature/venue-marketing-kit`; pendiente de revisión y merge del PR.

## Decisiones confirmadas

- Todas las sedes solicitan inicialmente los seis pilares existentes en el catálogo:
  `general-english`, `cambridge-exam-preparation`, `university-programmes`,
  `business-english`, `ielts-preparation` y `spanish-courses`.
- La selección se mantiene editable: cualquier slug activo adicional puede agregarse a un
  bundle futuro sin cambiar el servicio ni la base de datos.
- El paquete cubre las tres familias solicitadas: piezas sociales, brochure/documento A4 y
  presentación. Usa `square-v1`, `story-v1`, `portrait-v1`, `brochure-a4-v1` y
  `presentation-16x9-v1`; no se creó otro renderer.
- El CTA no se fija por sede en el catálogo: lo aporta el brief y lo decide quien diseña cada
  pieza. Si no viene en `brief_context`, la generación se rechaza.
- Mapa, QR, fotografía local y logos adicionales son assets opcionales del diseño. No se
  generan ni se asumen automáticamente; los campos pendientes permanecen en
  `official_contact_data.needs_confirmation`.

## Datos y procedencia

Cada `Branch` conserva `country`, `source_url` y un JSON estructurado en
`official_contact_data` con `location`, `contact`, `source_status` y `needs_confirmation`.
La migración inicial carga únicamente sedes publicadas en las fuentes siguientes:

- [IH México — Escuelas de Inglés en México](https://ihmexico.mx/escuelas-de-ingles-en-mexico/):
  24 registros publicados en el JSON-LD del directorio, incluidos los centros de examen que
  aparecen con ese nombre.
- [IH Colombia — Sedes](https://ihcolombia.com/sedes/): las 7 sedes mostradas por la página.
- [IH Lima — Sedes](https://ihlima.com/sedes/): Miraflores y Arequipa; San Borja se toma del
  footer oficial de la misma página, con los datos proporcionados para esa sede.
- [IH Santiago — Sedes](https://ihsantiago.cl/sedes/): Santiago/IELTS Chile, que es la sede
  expuesta por la página vigente consultada.

Los datos de dirección y contacto cargados desde esas fuentes tienen `source_status=confirmed`.
No se rellenan horarios, mapa, CTA ni assets locales: quedan explícitamente pendientes hasta que
el diseño o la operación los confirme. Si una sede nueva se crea con estado distinto de
`confirmed`, `generate_venue_kit` la bloquea.

## Reutilización técnica

El flujo es:

```text
Branch confirmado
    -> MaterialBundle(material_type=venue-kit)
    -> MaterialBundleItem por pieza
    -> DesignBrief -> Design -> DesignVersion -> revisión
```

Se reutilizan `MaterialBundle`, `MaterialBundleItem`, briefs hijos, revisión automática, validación
de logos y los renderers ya existentes. `venue-kit` actúa como tipo de paquete; los briefs de cada
pieza apuntan al `MaterialType` real del renderer (`social-post`, `brochure` o `presentation`).

La API expone los seis productos como prioridades del paquete y también mantiene visibles los
demás productos activos del catálogo. Si un bundle llega sin `product_slugs`, se completa con los
seis defaults confirmados; si trae una lista explícita, se valida contra el catálogo activo.

## Contexto requerido

```json
{
  "brand_logo_key": "ih-mexico-classic-png",
  "headline": "",
  "body": "",
  "cta": "",
  "audience": "",
  "objective": "",
  "additional_logo_keys": [],
  "copy_by_product": {}
}
```

El servicio agrega al brief la sede resuelta, su procedencia y los pendientes. El cuerpo renderizado
incluye el texto del brief más la dirección, ciudad, teléfono y email oficial disponible; el CTA
continúa siendo el texto aprobado por el diseño.

## Guardrails

- No se inventan productos, disponibilidad local, contactos, horarios, mapas ni CTAs.
- Un slug desconocido o deprecated produce `400` en la creación del bundle.
- Una sede sin dirección/teléfono, URL de fuente o `source_status=confirmed` produce `400` al
  generar.
- Los formatos futuros y productos adicionales se incorporan mediante catálogo/template aprobado;
  no se convierten automáticamente en piezas publicables.

## Pendientes operativos

- Confirmar y mantener horarios, mapas, QR, fotografías y CTA por pieza cuando una campaña los
  necesite.
- Revisar periódicamente las URLs oficiales y actualizar la migración/registro cuando cambie una
  sede o contacto.
- Validar con Marketing si los centros de examen de México deben tener tratamiento visual o CTA
  distinto al de una sede académica, aunque inicialmente comparten el paquete confirmado.
