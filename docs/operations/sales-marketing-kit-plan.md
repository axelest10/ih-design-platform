# Diseño de paquetería de marketing para ventas (`sales-kit`)

**Estado:** diseño aprobado para implementar el flujo genérico; no hay una oferta comercial
inicial sembrada porque el repositorio no contiene precios, promociones ni fechas vigentes
autorizadas.

## Objetivo

`sales-kit` produce un conjunto de piezas de conversión para una oferta o campaña comercial
concreta. La campaña es la fuente de verdad de precio, promoción, vigencia, copy aprobado y CTA.
El paquete no crea una oferta por sí mismo ni convierte el catálogo global de productos en una
promoción.

El flujo será:

```text
Product + Campaign confirmada
        -> MaterialBundle(material_type=sales-kit)
        -> MaterialBundleItem por deliverable
        -> DesignBrief -> Design -> DesignVersion -> revisión
```

## Qué necesita ventas que no necesitan `school-kit` ni `venue-kit`

| Dato | Por qué es específico de ventas | Fuente | Regla |
| --- | --- | --- | --- |
| Campaña/oferta | Define qué se vende ahora y evita copy genérico | `campaigns.Campaign` | Obligatoria en el bundle |
| Producto objetivo | Una pieza de ventas puede enfocarse en un producto, no en toda la oferta | `Campaign.product` o `product_slug` validado | Debe existir en catálogo activo |
| Precio/beneficio | La razón de conversión debe ser explícita y exacta | `Campaign.offer_data` | No se inventa ni se toma del copy libre |
| Vigencia | Evita publicar una oferta vencida | `starts_on`, `ends_on`, `offer_data` | La generación se bloquea fuera de vigencia |
| Copy aprobado | Reduce el riesgo de alterar términos comerciales | `approved_copy` | Debe existir para una pieza final |
| CTA de conversión | Acción concreta para ventas: cotizar, inscribirse, agendar, etc. | `offer_data.cta` o brief aprobado | Obligatorio y no inferido |
| Audiencia/segmento | Define el argumento de venta y canal | `offer_data.audience` o brief | Debe venir del contexto autorizado |
| Fuente y estado | Permite auditar quién autorizó la oferta | `offer_data.source_url`, `source_status` | `source_status=confirmed` requerido |

`offer_data` es JSON existente en `Campaign`; el diseño no crea otra tabla ni categorías de
producto. Para una campaña confirmada, la forma mínima esperada es:

```json
{
  "source_status": "confirmed",
  "source_url": "https://fuente-oficial/",
  "offer_type": "discount|bundle|benefit|information",
  "benefit": "Texto exacto aprobado",
  "price": null,
  "currency": null,
  "audience": "Segmento autorizado",
  "cta": "CTA aprobado",
  "validity_note": "Vigencia aprobada"
}
```

Los campos `price` y `currency` pueden ser `null` cuando la campaña no es una promoción de
precio; no se reemplazan con estimaciones. El renderer recibe solo valores validados.

## Qué reutiliza

- `MaterialBundle`, `MaterialBundleItem`, `DesignBrief`, `Design`, `DesignVersion` y revisión
  automática.
- `Product` y `Campaign` existentes; no se duplica el catálogo ni se crea una entidad “Oferta”.
- Validación de logos y assets oficiales.
- Templates y renderers existentes: `square-v1`, `story-v1`, `portrait-v1`, `brochure-a4-v1` y
  `presentation-16x9-v1`.
- El patrón de `school-kit`/`venue-kit`: piezas sociales por producto y documentos/presentación
  una vez por bundle.
- `needs_confirmation` y la procedencia en `brief_data`/`offer_data`.

## Qué es genuinamente distinto

- `campaign` es obligatorio; una sede puede faltar en otras paqueterías, pero ventas necesita una
  oferta o campaña resoluble.
- La generación valida estado activo y vigencia de la campaña, así como `source_status` y
  `approved_copy`.
- El contenido comercial crítico se compone desde la campaña: beneficio, precio si existe,
  vigencia y CTA. El texto libre del brief no puede sobrescribir esos valores.
- Si la campaña está vencida, aún no inició, está inactiva o no tiene fuente confirmada, el
  endpoint devuelve `400` y no crea piezas.
- Las piezas conservan el `campaign_id`, `product_slug` y snapshot de `offer_data` en
  `brief_data`, de modo que una futura edición de la campaña no reescriba versiones históricas.

## Formatos iniciales

Se implementan las tres familias ya aprobadas para paquetes anteriores:

1. Social: cuadrado, story y vertical por producto.
2. Documento A4: brochure de oferta por bundle.
3. Presentación 16:9: resumen comercial por bundle.

No se agregan reels, carruseles, landing pages ni envío de mensajes: no existe renderer ni
autorización para esos canales en este alcance.

## Guardrails y pendientes

- El repositorio no tiene una oferta vigente ni una fuente comercial aprobada. La referencia
  visual histórica `4x3-oferta-especial` se conserva como precedente, pero no se usa como datos
  de campaña.
- No se sembrará una campaña demo en producción ni se rellenarán precios, porcentajes, fechas o
  CTA por defecto.
- Queda como pendiente de coordinación entregar la primera `Campaign` confirmada con su fuente,
  producto, audiencia, beneficio, CTA y vigencia. El código genérico puede probarse con fixtures
  explícitamente marcados `source_status=confirmed`.
- Si Marketing necesita una regla de promoción distinta de `offer_data`, deberá documentarla y
  versionarla antes de ampliar el contrato.
