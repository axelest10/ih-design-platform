# Reglas de logotipo — International House México

Fuente: `International House Brand Guidelines (1).pdf` (manual oficial global). Ningún
documento de México trata reglas de logotipo — toda esta sección proviene exclusivamente del
manual global.

## Zona de exclusión (clear space / safe zone)

> "The 'exclusion zone' is the area of clear space around the brand mark. No other element
> should encroach on this space. The exclusion zone is equivalent to half the diameter of the
> IH globe of the brand mark."

Es decir: la zona de exclusión mínima alrededor del logo equivale a **la mitad del diámetro
del globo** que forma parte del isotipo (unidad relativa "X" en los diagramas del manual, no
una cifra absoluta en px/mm).

## Tamaño mínimo

**No documentado en el manual global.** Se revisó visualmente la sección "Logo Size" del PDF
(renderizada a 150dpi el 2026-08-05, no solo el texto extraído): la página solo muestra los dos
formatos de lockup permitidos (isotipo + wordmark en 2 líneas, e isotipo + wordmark en 1 línea
+ lista de sedes) y confirma que el artwork se crea de forma centralizada y no debe alterarse.
**No hay ninguna cifra de tamaño mínimo de reproducción en px/mm/pt en ningún lugar del
manual.**

### Tamaño mínimo designado por extensión MX (no es cifra oficial del manual)

Por instrucción del proyecto, ante la ausencia de una cifra oficial, se **designa** un tamaño
mínimo derivado de las reglas que sí están documentadas en el manual — no inventado:

- La regla de zona de exclusión (mitad del diámetro del globo) exige espacio proporcional
  alrededor del logo; un logo demasiado pequeño vuelve esa zona de exclusión inviable de
  respetar en la práctica.
- La regla de video/signature screen fija el logo en **30% del ancho de pantalla** como única
  cifra de tamaño relativo que sí es oficial — usada aquí como ancla de proporción, no de
  tamaño absoluto.
- La prohibición explícita de "expandir, distorsionar o hacer ilegible" el logo implica que el
  texto del wordmark ("International House", nombres de sede, tagline) debe permanecer legible
  en cualquier reproducción.

Con esa base, se designan los siguientes mínimos (aplican para impresión y pantalla; **estado:
`mx_designated`, pendiente de aprobación formal del cliente/Marketing**):

| Variante del lockup | Mínimo digital (alto) | Mínimo impreso (alto) | Razonamiento |
| --- | --- | --- | --- |
| Isotipo solo (círculo "ih") | 24px | 10mm | Por debajo de esto el trazo de las letras "ih" pierde legibilidad y la zona de exclusión se vuelve impracticable. |
| Isotipo + wordmark 1 línea ("International House") | 32px | 15mm | El wordmark necesita suficiente x-height para no distorsionarse al escalar. |
| Isotipo + wordmark + texto secundario (sedes/tagline, tipografía más pequeña que el wordmark) | 48px | 20mm | El texto secundario es notablemente más chico que "International House"; a 32px ese texto cae por debajo del umbral de legibilidad. |

Si el cliente confirma una cifra oficial distinta (p. ej. desde una versión más completa del
manual o desde Marketing), esta tabla debe reemplazarse y el `status` pasar de `mx_designated`
a `approved`.

## Variantes de color permitidas y sus fondos

| Variante del logo | Fondo permitido |
| --- | --- |
| Clásico (negro + Knowledge Blue) | Fondo blanco |
| Negro | Fondo blanco (máximo contraste) |
| Blanco | Fondo Knowledge Blue |
| Clásico o versión con texto blanco | Fotografía (fondo fotográfico) |

Cita textual (sección "Logo Application / Background"):

> "Depending on the background, the brand can use a combination of the colours: knowledge
> blue, black, and white. On white backgrounds, use the classic logo (black and knowledge
> blue). For the highest contrast, use the background in white and the logo in black. On the
> knowledge blue background, use the logo in white. On a photo background, use the classic
> logo (Black and Knowledge Blue) or its version with white text (White and Knowledge Blue)."

## Uso incorrecto — prohibido

1. Cambiar el color del logo.
2. Expandir o distorsionar el logo.
3. Delinear (outline) cualquier elemento del logo.
4. Agregar una sombra (drop shadow) detrás del logo.
5. Agregar texto propio debajo o cerca del logo.
6. Agregar el nombre de la escuela propia bajo el logo por cuenta propia — usar únicamente el
   artwork provisto para cada escuela.
7. Cambiar la opacidad del logo.
8. Colocar el logo sobre un fondo demasiado oscuro para ser legible.
9. Usar cualquier fondo de color de la paleta que no sea blanco para el logo clásico
   (negro + Knowledge Blue). Ningún otro color de la paleta está permitido como fondo del logo
   clásico.
10. Usar fondos de bajo contraste con el logo.
11. Usar el logo sobre un fondo que use un tono de azul distinto a Knowledge Blue.
12. Usar fotografías de bajo contraste con el logo.

## Aplicación en video / signature screen

- Fondos planos: el logo debe ocupar **30% del ancho de pantalla**.
- Fondos con fotografía: logo al **30% del ancho de pantalla**, con un espacio mínimo del
  **5%** entre el borde de la foto y el logo; alineado a la izquierda o derecha (nunca
  centrado, para no obstruir la fotografía), posicionado donde exista mejor contraste.
- Regla citada: "The IH brand mark should be sized at 30% of the screen width and placed
  top-right. Make sure to maintain the contrast between the background and logo."

## Marca IHWO Member y dual branding (co-branding con logo de escuela)

- El logo de miembro IHWO puede usarse junto al logo de la escuela, respetando la misma zona
  de exclusión (mitad del diámetro del globo).
- Reglas de dual branding:
  - La altura de ambos logos debe ser siempre igual.
  - Se separan con una barra/slash cuya altura es el 80% de la altura de los logos (versión
    horizontal) o cuya longitud es el 80% de la longitud de los logos (versión vertical).
  - Los diseños dual-branded deben incluir: marca IH a tamaño completo, un gráfico rainbow (en
    la página o como detalle), tipografía Aptos u Open Sans, y los colores de marca IH para
    titulares y texto.
- Incorrecto en dual branding:
  - El logo de IH World siempre debe ir primero, seguido del logo de la escuela.
  - No está permitido agrandar un logo para igualar longitudes (deben ser iguales en altura,
    con ancho proporcional).
  - No está permitido alinear lateralmente los logos en la versión vertical (deben ir
    centrados).
  - La línea separadora no puede exceder la altura/ancho de los logos.

## Validación automática

`backend/branding/services/validators.py::validate_logo` valida que todo logo referenciado por un
diseño exista en `brand/assets/logos/manifest.yaml` con `approved: true`. Cualquier archivo de
logo no registrado (o registrado con `approved: false`) se rechaza. Ver
`tests/test_branding_assets.py`.
