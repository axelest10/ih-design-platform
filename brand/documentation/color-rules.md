# Reglas de color — International House México

Fuente principal: `International House Brand Guidelines (1).pdf` (paleta oficial global).
Extensiones de México confirmadas por el cliente el 2026-08-05 en `brand/tokens/colors.yaml` y
`brand/product-colors/authorized-colors.yaml`.

## Paleta oficial (8 colores)

### Primarios

| Nombre oficial | Token | HEX | RGB | CMYK |
| --- | --- | --- | --- | --- |
| Knowledge Blue | `knowledge` | #3B44B5 | 59, 68, 181 | 67, 62, 0, 29 |
| Technology Purple | `technology` | #923472 | 146, 52, 114 | 0, 64, 22, 43 |
| Youth Green | `youth` | #B7DB6E | 183, 219, 110 | 16, 0, 50, 14 |
| Joy Yellow | `joy` | #F4CF80 | 244, 207, 128 | 0, 15, 48, 4 |

### Secundarios

| Nombre oficial | Token | HEX | RGB | CMYK |
| --- | --- | --- | --- | --- |
| Light Orange | `light` | #F4AB63 | 244, 171, 99 | 0, 30, 59, 4 |
| Salmon | `salmon` | #F06C6A | 240, 108, 106 | 0, 55, 56, 6 |
| Pink | `pink` | #E070A2 | 224, 112, 162 | 0, 50, 28, 12 |
| Green | `green` | #28AE62 | 40, 174, 98 | 77, 0, 44, 32 |

### Extensión México confirmada

| Nombre | Token | HEX | Estado |
| --- | --- | --- | --- |
| Rojo IELTS (oficial México) | `ielts_red` | #E31736 | Confirmado por el cliente 2026-08-05 |

No forma parte de la paleta de 8 colores del manual global; es exclusivo del pilar IELTS en
México y no debe usarse fuera de ese contexto.

## Colores por producto/pilar

Ver `brand/product-colors/authorized-colors.yaml` para la tabla completa (color principal,
secundario, fondo y CTA por cada uno de los 6 pilares: Inglés General, Cambridge, University
Programmes, Empresas, IELTS, Spanish Courses). Fuente confirmada por el cliente:
`IH_BRANDING_MARCA.docx`, tabla "Sistema de Colores por Pilar" (idéntica a
`IH_Mexico_Sistema_Diseno_Web.docx`).

## Rainbow institucional

Regla de oro (cita textual del manual): *"Always use the rainbow starting from the colour
salmon and ending in the colour yellow."*

- Nunca reordenar los colores del rainbow.
- Nunca usar un rainbow que inicie en amarillo/joy.
- Solo un modelo de rainbow por pieza; puede duplicarse pero nunca reflejarse, rotarse ni
  escalarse de forma distinta.
- Nunca usarlo en diagonal — solo horizontal o vertical.
- El set de 8 colores aprobado es el del manual oficial (incluye Light Orange #F4AB63). Se
  evaluó y **descartó** una variante documentada solo en un docx de México que sustituía Light
  Orange por un color "Teal" (#407B98) no presente en ninguna paleta oficial — decisión del
  cliente, 2026-08-05.

## Combinaciones y contraste

Reglas citadas textualmente del manual oficial:

- "It is recommended to use white or black for text elements."
- "It is recommended to use black or white for text elements and blue and white for
  backgrounds."
- "Don't combine too many colours."
- "Do not create gradients with brand colours."
- "Do not combine low contrast colours."
- "Do not modify the colours."

Excepción documentada (sección "Digital ad with graphics"): al representar personas, usar
tonos de piel naturales en vez de la paleta de marca; símbolos universalmente reconocidos
(planetas, semáforos, banderas) deben conservar sus colores naturales o estándar.

**Nota sobre accesibilidad:** el manual oficial no da una cifra numérica de ratio de contraste
en el texto extraído (solo un título de sección "Contrast and Accessible Colours" sin cifra
asociada). El valor de referencia 4.5:1 / WCAG AA usado en este sistema proviene de un
checklist de México (`IH_Mexico_Sistema_Diseno_Web.docx`), no del manual global — ver
`accessibility-rules.md`.

## Qué evitar

- No crear degradados con los colores de marca — siempre fondos sólidos.
- No combinar colores de bajo contraste.
- No modificar ni aproximar los valores HEX oficiales.
- No inventar colores nuevos fuera de la paleta de 8 + la extensión IELTS confirmada.
- No mezclar el color principal de un pilar con el de otro pilar en la misma pieza.
- No usar el rojo IELTS fuera del pilar IELTS.

## Pendiente de confirmación

- Mapeo de nombres de producto usado en `Color por producto.pdf` ("Live!", "UP") — no se
  confirmó si son sinónimos de "Inglés General" y "University Programmes" o productos/campañas
  distintas. Ver `authorized-colors.yaml -> alternate_sources_not_used`.
