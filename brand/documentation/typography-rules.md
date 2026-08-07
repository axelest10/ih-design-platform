# Reglas de tipografía — International House México

Fuente principal: `International House Brand Guidelines (1).pdf`. Escala tipográfica detallada
(H1-H4, body, caption, CTA, badge) es una extensión documentada en
`IH_Mexico_Sistema_Diseno_Web.docx` / `IH_Sistema_Colores_v2.docx` (idénticas entre sí), no
aparece en el manual global.

## Tipografía principal (titulares): Aptos

> "Golden rule: Always use Aptos as the primary typeface."

Aptos es la tipografía por defecto de Microsoft Office desde 2023 (antes "Bierstadt"),
diseñada con base en Helvetica y Arial. Pesos documentados: Regular, Semibold, Bold.

**Licencia: sin confirmar.** Ver `brand/assets/fonts/README.md` — pregunta pendiente para el
cliente.

Fallback documentado (extensión MX): `Aptos, Arial, sans-serif`.

## Tipografía secundaria (cuerpo): Open Sans

> "Golden rule: Always use Open Sans as a secondary typeface."

Tipografía humanista sans-serif de código abierto (2011), con aperturas amplias y x-height
grande — alta legibilidad en pantalla y tamaños pequeños. Pesos documentados: Light, Regular,
Semibold, Bold. Licencia: **SIL Open Font License 1.1** (incluida en
`brand/assets/fonts/open-sans/OFL.txt`).

Fallback documentado: `'Open Sans', sans-serif`.

## Interlineado (leading)

| Elemento | Interlineado |
| --- | --- |
| Titulares/headings | 1.1x (110%) |
| Subtítulos | 1.2x (120%) |
| Cuerpo de texto | 1.4x (140%) |

## Tracking (espaciado entre letras)

| Elemento | Figma | Adobe |
| --- | --- | --- |
| Titulares/headings | -2% | -20 pt |
| Subtítulos | -1% | -10 pt |
| Cuerpo de texto | 0% | 0 pt |

## Jerarquía y pesos

- Para títulos: usar el peso **semibold** de Aptos (no bold por defecto) — atrae atención sin
  sensación de pesadez.
- Para cuerpo: usar Open Sans **Light o Regular**.
- Para enfatizar una palabra/frase: subir un solo nivel de peso (p. ej. de Regular saltar
  directo a Semibold, sin pasar por "medium").
- Usar como máximo **3 tamaños de fuente** por pieza de comunicación.

## Escala tipográfica (extensión MX — ver `brand/tokens/typography.yaml -> type_scale`)

| Estilo | Tipografía | Peso | Tamaño | Interlineado | Uso |
| --- | --- | --- | --- | --- | --- |
| H1 Display | Aptos | Bold | 56px (móvil máx. 32px) | 64px | Hero — uno solo por página |
| H2 Section | Aptos | Semibold | 40px (móvil máx. 24px) | 48px | Títulos de sección |
| H3 Subsection | Aptos | Semibold | 28px | 36px | Subtítulos de bloque |
| H4 Card Title | Aptos | Semibold | 22px | 28px | Títulos de card/modal |
| Body Large | Open Sans | Regular | 18px | 28px | Párrafos bajo el hero |
| Body Base | Open Sans | Regular | 16px | 24px | Cuerpo estándar |
| Body Small | Open Sans | Regular | 14px | 20px | Texto secundario/labels |
| Caption | Open Sans | Regular | 12px | 18px | Captions/metadatos/legal |
| CTA/Button | Aptos | Semibold | 16px | — | Botones (mayúsculas opcional) |
| Badge/Tag | Open Sans | Bold | 12px, tracking 1% | — | Tags/badges/pills |

## Uso incorrecto

- No mezclar alineaciones de texto en párrafos cercanos.
- No distorsionar las tipografías en texto de cuerpo.
- No mezclar tipografías distintas dentro del mismo bloque de texto.
- No justificar el texto.

## Pendiente de confirmación

- Licencia de uso/redistribución de los archivos `.ttf` de Aptos.
