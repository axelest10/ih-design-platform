# Reglas de accesibilidad — International House México

## Matriz oficial de contraste (manual global, página "Accessible Brand Colours")

El PDF oficial (`International House Brand Guidelines (1).pdf`) incluye una página dedicada,
"Contrast and Accessible Colours", con una **matriz de contraste calculada para las 10
combinaciones de color institucionales** (8 colores de marca + blanco + negro) y su nivel de
cumplimiento WCAG. Esta cifra no era extraíble como texto plano (`pdftotext`) porque está
renderizada como imagen/tabla; se confirmó visualmente renderizando la página a 150dpi el
2026-08-05. Reemplaza la sección "pendiente de confirmación" de versiones anteriores de este
documento.

### Estándar de cumplimiento (leyenda oficial del manual)

| Símbolo | Nivel | Umbral |
| --- | --- | --- |
| ✅ AAA | Pass | ratio ≥ 7.0 |
| ✅ AA | Pass | ratio ≥ 4.5 |
| ⚠️ AA18 | Pass, solo texto grande | ratio ≥ 3.0 |
| ❌ DNP | Does Not Pass | ratio < 3.0 |

Estos umbrales **coinciden exactamente con WCAG 2.1** (SC 1.4.3 texto normal AA = 4.5:1, texto
grande AA = 3:1; SC 1.4.6 AAA = 7:1). El manual no lo nombra explícitamente como "WCAG 2.1",
pero los valores son idénticos, así que se documenta como tal.

### Matriz de contraste (ratio de contraste real, calculado por IH)

Colores: Green `#28AE62`, Knowledge Blue `#3B44B5`, Technology Purple `#923472`, Youth Green
`#B7DB6E`, Pink `#E070A2`, Salmon `#F06C6A`, Light Orange `#F4AB63`, Joy Yellow `#F4CF80`,
White `#FFFFFF`, Black `#000000`.

| vs. → | Green | Knowledge | Technology | Youth | Pink | Salmon | Light Or. | Joy | White | Black |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Green** `#28AE62` | — | 2.73 ❌ | 2.48 ❌ | 1.83 ❌ | 1.04 ❌ | 1.04 ❌ | 1.48 ❌ | 1.92 ❌ | 2.87 ❌ | 7.32 ✅AAA |
| **Knowledge** `#3B44B5` | 2.73 ❌ | — | 1.10 ❌ | 4.99 ✅AA | 2.62 ❌ | 2.63 ❌ | 4.05 ⚠️AA18 | 5.25 ✅AA | 7.84 ✅AAA | 2.68 ❌ |
| **Technology** `#923472` | 2.48 ❌ | 1.10 ❌ | — | 4.52 ✅AA | 2.37 ❌ | 2.39 ❌ | 3.67 ⚠️AA18 | 4.76 ✅AA | 7.10 ✅AAA | 2.96 ❌ |
| **Youth** `#B7DB6E` | 1.83 ❌ | 4.99 ✅AA | 4.52 ✅AA | — | 1.91 ❌ | 1.89 ❌ | 1.23 ❌ | 1.05 ❌ | 1.57 ❌ | 13.37 ✅AAA |
| **Pink** `#E070A2` | 1.04 ❌ | 2.62 ❌ | 2.37 ❌ | 1.91 ❌ | — | 1.01 ❌ | 1.55 ❌ | 2.01 ❌ | 3.00 ⚠️AA18 | 7.01 ✅AAA |
| **Salmon** `#F06C6A` | 1.04 ❌ | 2.63 ❌ | 2.39 ❌ | 1.89 ❌ | 1.01 ❌ | — | 1.54 ❌ | 2.00 ❌ | 2.98 ❌ | 7.06 ✅AAA |
| **Light Orange** `#F4AB63` | 1.48 ❌ | 4.05 ⚠️AA18 | 3.67 ⚠️AA18 | 1.23 ❌ | 1.55 ❌ | 1.54 ❌ | — | 1.30 ❌ | 1.94 ❌ | 10.85 ✅AAA |
| **Joy Yellow** `#F4CF80` | 1.92 ❌ | 5.25 ✅AA | 4.76 ✅AA | 1.05 ❌ | 2.01 ❌ | 2.00 ❌ | 1.30 ❌ | — | 1.49 ❌ | 14.08 ✅AAA |
| **White** `#FFFFFF` | 2.87 ❌ | 7.84 ✅AAA | 7.10 ✅AAA | 1.57 ❌ | 3.00 ⚠️AA18 | 2.98 ❌ | 1.94 ❌ | 1.49 ❌ | — | 21.00 ✅AAA |
| **Black** `#000000` | 7.32 ✅AAA | 2.68 ❌ | 2.96 ❌ | 13.37 ✅AAA | 7.01 ✅AAA | 7.06 ✅AAA | 10.85 ✅AAA | 14.08 ✅AAA | 21.00 ✅AAA | — |

### Combinaciones aprobadas para texto normal (AA o mejor) — usar estas primero

- **Negro sobre**: Green, Youth Green, Pink, Salmon, Light Orange, Joy Yellow, White (todas ✅AAA).
- **Blanco sobre**: Knowledge Blue (7.84 ✅AAA), Technology Purple (7.10 ✅AAA), Negro (21.00 ✅AAA).
- **Knowledge Blue sobre**: Youth Green (4.99 ✅AA), Joy Yellow (5.25 ✅AA), Blanco (7.84 ✅AAA).
- **Technology Purple sobre**: Youth Green (4.52 ✅AA), Joy Yellow (4.76 ✅AA), Blanco (7.10 ✅AAA).

### Combinaciones que solo pasan para texto grande (AA18, ≥18pt o ≥14pt bold) — usar con cuidado

- Knowledge Blue sobre Light Orange (4.05), Technology Purple sobre Light Orange (3.67),
  Blanco sobre Pink (3.00).

### Combinaciones prohibidas (DNP) — nunca usar como texto/fondo

- Cualquier par entre colores del rainbow que no involucre blanco o negro y no esté en las
  listas anteriores (p. ej. Green sobre cualquier color que no sea negro, Salmon sobre
  cualquier color que no sea negro, Pink sobre cualquier color que no sea negro/blanco-AA18).

## Reglas de texto explícitas del manual oficial

- "It is recommended to use white or black for text elements."
- "Do not combine low contrast colours."
- "Using low contrast background colours with the logo is not permitted."
- "Using photographs with low contrast with the logo is not permitted."
- Página "Colour Application — Incorrect Application": no combinar demasiados colores, no crear
  degradados con colores de marca, no combinar colores de bajo contraste, no modificar los
  colores.

## Extensión de México (documentada, no del manual global)

`IH_Mexico_Sistema_Diseno_Web.docx` (checklist de lanzamiento, sección 9.3) especifica de forma
independiente: "Revisión de contraste de colores: mínimo WCAG AA (ratio 4.5:1)." Esto coincide
con el estándar AA de la matriz oficial de arriba, así que ambas fuentes son consistentes entre
sí — no hay contradicción, la extensión MX simplemente generaliza el mismo umbral como regla de
checklist de lanzamiento.

## Reglas prácticas derivadas (aplicación de diseño)

- Verificar cualquier combinación texto/fondo contra la matriz de arriba antes de aprobar una
  pieza; si el par no aparece explícitamente como ✅AA o ✅AAA, usar negro o blanco en su lugar.
- Los CTAs deben usar siempre texto blanco o negro sobre el color del pilar (nunca un color de
  marca sobre otro color de marca fuera de las combinaciones ✅AA/✅AAA listadas).
- Botones CTA en mobile: mínimo 44px de altura (touch target estándar de accesibilidad móvil,
  documentado en `layout-rules.md`).
- Iconografía: incluir siempre `aria-label` (regla de México, sección de íconos).

## Excepción documentada (representación de personas y símbolos)

Sección "Digital ad with graphics" del manual: al representar personas, usar tonos de piel
naturales en vez de la paleta de marca; símbolos universalmente reconocidos (planetas,
semáforos, banderas) deben conservar sus colores naturales o estándar, no los colores
institucionales.
