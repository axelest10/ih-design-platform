# Reglas de composición y layout — International House México

El manual oficial global solo tiene una sección "Grids" breve y sin cifras concretas en el
texto extraído: *"Creating a grid allows you to build consistent communication materials. The
grid system should be used for the design of all materials wherever possible, whatever size
they are."* Todas las cifras de esta página son una **extensión de México**
(`IH_Sistema_Colores_v2.docx` / `IH_Mexico_Sistema_Diseno_Web.docx`).

## Grid (sistema de diseño Figma/web)

| Breakpoint | Columnas | Gutter | Margen lateral | Ancho de referencia |
| --- | --- | --- | --- | --- |
| Desktop | 12 | 72px | 80px | ≥1440px |
| Tablet | 8 | 24px | 40px | ≥768px |
| Mobile | 4 | 16px | 20px | ≥375px |

Auto layout: "Hug" en ambas dimensiones para componentes; "Fill" para contenedores de sección.

## Espaciado

Unidad base: **8px**. Escala: 8, 16, 24, 32, 48, 64, 80, 120px.

## Bordes y sombras

| Elemento | Radio |
| --- | --- |
| Botones | 8px |
| Cards | 12px |
| Inputs | 8px |
| Pills/badges | 100px (full round) |

| Nivel | Sombra |
| --- | --- |
| 1 | `0 2px 8px rgba(0,0,0,0.08)` |
| 2 | `0 8px 24px rgba(0,0,0,0.12)` |
| 3 | `0 16px 48px rgba(0,0,0,0.16)` |
| Card | `0 8px 24px rgba(0,0,0,0.10)` |

## Breakpoints de diseño responsivo (sistema distinto al grid — extensión MX)

- Desktop: >1200px.
- Tablet: 768-1199px.
- Mobile: <767px.

Reglas: nunca ocultar CTAs en mobile; H1 móvil máx. 32px, H2 móvil máx. 24px; imágenes hero en
mobile verticales o cuadradas (no el mismo recorte que desktop); formularios en mobile al 100%
del ancho sin columnas internas; botones CTA en mobile con mínimo 44px de altura (touch
target).

## CTAs y botones

| Tipo | Estilo |
| --- | --- |
| CTA Primario | Fondo color del pilar, texto blanco, radio 8px, sin outline. |
| CTA Secundario | Outline en color del pilar, texto en color del pilar, mismo tamaño. |
| CTA WhatsApp | Verde #25D366, ícono WhatsApp, texto "Escríbenos", siempre visible en mobile. |
| CTA Flotante | Solo WhatsApp global, posición fixed bottom-right, z-index alto. |
| Submit de formulario | Fondo color del pilar, texto blanco, radio 8px, ancho 100%, Aptos Semibold 16px. |

## Estructura de bloque Hero

- Dimensiones: 100vw × 100vh (mínimo 600px de alto en desktop); mobile auto-height, mínimo
  480px.
- Fondo: imagen con overlay sólido del color del pilar (opacidad 70-80%) — nunca gradiente.
- Tipografía: H1 Aptos Bold 56px desktop / 36px mobile; subtítulo Open Sans Regular 20px / 16px
  mobile.
- Badge superior: fondo oscuro #1A2566, texto en color del pilar o blanco.

## Estructura recomendada de una landing (extensión MX)

Orden documentado: Hero (obligatorio) → Trust/confianza (recomendado) → Beneficios en
Knowledge Blue (obligatorio) → Modalidades (recomendado) → Para quién (recomendado) →
Metodología (recomendado) → Stats en color del pilar (obligatorio) → Testimonios
(obligatorio) → Formulario de lead capture en Youth Green (obligatorio) → FAQ (recomendado) →
CTA final en color del pilar oscuro (obligatorio) → Footer (obligatorio).

**Nota:** los dos documentos de México usan nomenclatura de bloques ligeramente distinta entre
sí para conceptos equivalentes (p. ej. "NIVELES-01"/"TRANSFORMACION-01" en un documento vs.
"STATS-01"/"MODULOS-01" en el otro). Se documenta el concepto funcional de cada bloque; el
nombrado exacto de componentes debe definirse al construir el sistema de plantillas.

## Qué evitar en construcción de piezas/web

- Tablas HTML para layouts.
- Estilos inline.
- Imágenes sin optimizar (máximo 200KB).
- Más de 3 plugins de slider distintos en el mismo sitio.
- `background-attachment: fixed` en mobile.
- Elementos animados que impidan hacer clic en CTAs.
- Gradientes con los colores de marca — siempre fondos sólidos.
- Duplicar bloques manualmente en vez de usar componentes reutilizables.
