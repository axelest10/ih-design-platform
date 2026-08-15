# Plan de paquetería de marketing para sedes (`venue-kit`)

**Estado:** diseño inicial; bloqueado para implementación hasta confirmar los datos de negocio
indicados al final.

**Alcance de esta fase:** definir el contrato de datos, la reutilización técnica y las decisiones
pendientes para una paquetería de una sede/sucursal de International House. No se crean modelos,
productos, templates, endpoints, servicios ni contenido comercial en esta fase.

## Objetivo

`venue-kit` debe producir piezas localizadas para una sede concreta, no una copia de `school-kit`
con el nombre de una ciudad. La sede es la unidad comercial y operativa: sus datos de contacto,
ubicación, programas realmente ofrecidos y CTA deben provenir de fuentes confirmadas.

La salida debe conservar el flujo existente de piezas independientes:

```text
Branch / datos confirmados
        ↓
MaterialBundle (material_type = branch-kit)
        ↓
MaterialBundleItem por deliverable
        ↓
DesignBrief → Design → DesignVersion → revisión
```

## Qué necesita una pieza de sede que `school-kit` no necesita

| Campo o dato | Por qué es específico de sede | Fuente propuesta | Estado actual |
| --- | --- | --- | --- |
| `branch` estable | Identifica la sede, no solo el país o una campaña | `catalog.Branch` | El modelo ya existe y tiene `code`, `name`, `city` y `official_contact_data`. |
| País/entidad de marca | Determina logos, colores y acceso regional | Relación/configuración oficial de la sede | `Branch` no tiene hoy un campo de país explícito; requiere decisión. |
| Dirección física | Permite visita y localización | Registro oficial de la sede | No debe inferirse desde `city`. |
| Teléfono, WhatsApp, email y web local | CTA accionable y contacto correcto | `official_contact_data` o fuente confirmada | El JSON existe, pero su contrato de campos no está estandarizado. |
| Horarios y modalidad | Evita prometer atención o clases no disponibles | Fuente operativa de la sede | Pendiente de confirmar por sede. |
| Programas ofrecidos por esa sede | `product-catalog` es global/por país, no prueba disponibilidad local | Allowlist por sede o input aprobado | No se debe derivar automáticamente del catálogo general. |
| Ubicación/mapa | Diferencia una sede física de una campaña nacional | URL, imagen o coordenadas aprobadas | No se debe dibujar ni inventar un mapa. |
| CTA local | Puede ser visita, WhatsApp, formulario o web | Brief/campaña aprobada | Debe confirmarse junto con el contacto. |

Los campos no confirmados deben conservar `needs_confirmation` en el contexto, validación o
manifest de la pieza. No se rellenarán con valores por defecto que parezcan hechos reales. Si falta
un dato imprescindible para una pieza final, la generación debe detenerse o producir únicamente un
borrador marcado explícitamente como pendiente; nunca una pieza promocional lista para publicar.

## Reutilización directa de `school-kit`

Se reutilizaría el patrón existente, no una segunda arquitectura:

- `MaterialBundle`, `MaterialBundleItem`, briefs hijos y versiones independientes.
- `branch` como relación existente del bundle y de cada `DesignBrief`.
- `MaterialType`/`MaterialTemplate` versionados y manifestados.
- Validación de logos oficiales y logos secundarios mediante las reglas existentes.
- Catálogo de productos como fuente de referencia, manteniendo `status` y `needs_confirmation`.
- Revisión automática y estados de `DesignVersion`; una pieza pendiente no se convierte en aprobada.
- Renderers existentes HTML/SVG, PDF y PPTX; la selección depende del deliverable aprobado.
- Flujo de generación asíncrona cuando la implementación se haga sobre la arquitectura de Celery.

El servicio no debe copiar literalmente todas las reglas de `school_kit.py`. Conviene extraer
helpers compartidos para logos, contexto, versionado y revisión solo cuando exista un caso real y
con tests que demuestren que `school-kit` no cambia de comportamiento.

## Qué es genuinamente distinto

`venue-kit` necesita una capa de contexto local y validación de disponibilidad:

1. Resolver una sede concreta y verificar que está activa y autorizada para el país/entidad.
2. Validar que cada programa seleccionado está permitido para esa sede, no solo que existe en
   `brand/knowledge/product-catalog.yaml/json`.
3. Separar datos nacionales de datos locales: el logo/identidad puede venir del país, pero la
   dirección, contacto, horarios y CTA deben venir de la sede.
4. Registrar la procedencia y el estado de confirmación de cada dato que entra en copy o layout.
5. Impedir que un cambio de contacto de una sede reescriba versiones históricas de piezas ya
   generadas.

## Contrato de contexto propuesto

El contrato definitivo depende de las confirmaciones de Axel, pero la forma prevista es un contexto
explícito, versionable y no un conjunto de strings ocultos dentro del servicio:

```json
{
  "branch_code": "sede-confirmada",
  "country": "MX",
  "brand_logo_key": "ih-mexico-classic-png",
  "program_slugs": [],
  "location": {
    "city": "",
    "address": "",
    "map_url": ""
  },
  "contact": {
    "phone": "",
    "whatsapp": "",
    "email": "",
    "website": "",
    "hours": ""
  },
  "cta": "",
  "source_status": "needs_confirmation"
}
```

Este JSON es una propuesta de contrato, no un valor para sembrar en el catálogo. `program_slugs`
debe ser una selección confirmada; una lista vacía no significa “todos los productos”. `map_url`,
contacto y horarios solo se usarán si proceden de una fuente aprobada. El servicio deberá mantener
la distinción entre `confirmed`, `inferred` y `needs_confirmation`, siguiendo el guardrail que ya
usa el catálogo para no convertir una inferencia en una regla comercial.

## Formatos candidatos y reutilización de renderers

La propuesta técnica inicial es reutilizar únicamente lo que ya funciona:

| Necesidad | Candidato | Renderer existente |
| --- | --- | --- |
| Post principal | `square-v1` | HTML/SVG |
| Story/CTA | `story-v1` | HTML/SVG |
| Pieza vertical informativa | `portrait-v1` | HTML/SVG |
| Brochure o ficha de sede | `brochure-a4-v1` u otro template aprobado | PDF |
| Presentación para visita/ventas | `presentation-16x9-v1` | PPTX |

No se considera implementado ningún formato adicional solo porque el enum lo permita. `reel`,
`carousel` y otros formatos necesitan un template y renderer real antes de entrar al paquete.
Un mapa, QR, fotografía de la sede o bloque de contacto se tratará como asset/contexto aprobado;
no se generará visualmente una ubicación que no exista en una fuente confirmada.

## Flujo de validación propuesto

1. Validar `branch_code`, estado activo, país y logo contra las fuentes existentes.
2. Validar que la selección de programas tenga una autorización específica de sede.
3. Validar los campos de contacto y ubicación requeridos por cada deliverable.
4. Construir el brief hijo con `brief_data` versionado y procedencia por campo.
5. Rechazar campos faltantes para una pieza final o marcar el bundle completo como
   `needs_confirmation` para revisión; no sustituirlos con copy inventado.
6. Generar cada pieza con el renderer existente y conservar su `DesignVersion` independiente.
7. Ejecutar revisión automática y mantener la revisión humana/publicación separadas de la
   generación.

## Preguntas agrupadas que bloquean la implementación

Estas son las tres confirmaciones que deben resolverse juntas antes de crear catálogo o código:

1. **Identidad y datos oficiales de la sede:** ¿qué sede y país serán el primer caso? ¿Cuál es la
   fuente autorizada para dirección, teléfono/WhatsApp, email, web, horarios, modalidad y mapa? ¿Se
   amplía `Branch` con país/dirección o se normaliza `official_contact_data`?
2. **Oferta local:** ¿qué programas exactos ofrece esa sede y quién mantiene la allowlist? ¿Se
   seleccionan manualmente slugs ya presentes en `product-catalog`, se necesita una relación
   programa-sede, o existe otra fuente confirmada? No habrá productos por defecto.
3. **Paquete inicial y CTA:** ¿qué deliverables entran en la primera versión —social, PDF,
   presentación o los tres— y cuál es el CTA aprobado? También debe confirmarse si se permite mapa,
   QR, fotografía de sede y logos adicionales.

Hasta recibir esas respuestas y la luz verde de Axel, esta rama se detiene en el documento de
diseño. No se implementan modelos, migraciones, servicios, templates, endpoints, seeds de catálogo
ni tests de `venue-kit`.
