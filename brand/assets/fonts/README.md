# Tipografías — International House México

## Open Sans (`open-sans/`)

Incluida en este repositorio. Licencia: **SIL Open Font License 1.1** (`open-sans/OFL.txt`).
Uso y redistribución libres bajo los términos de esa licencia. Variable fonts:
`OpenSans-VariableFont_wdth,wght.ttf` y `OpenSans-Italic-VariableFont_wdth,wght.ttf`.

## Aptos (`aptos/`) — investigado 2026-08-05, redistribución restringida por licencia estándar

Los archivos `.ttf` de Aptos **NO se incluyeron** en este repositorio. Aptos es la tipografía
por defecto de Microsoft Office desde 2023 (originalmente llamada "Bierstadt").

**Resultado de la investigación (2026-08-05):**

- Microsoft sí publica una descarga oficial y gratuita de Aptos:
  [microsoft.com/en-us/download/details.aspx?id=106087](https://www.microsoft.com/en-us/download/details.aspx?id=106087).
- Sin embargo, la licencia estándar que acompaña esa descarga autoriza **usar** la fuente para
  crear, mostrar e imprimir contenido (y embeberla en documentos según las restricciones de
  embedding del propio archivo de fuente), pero **no autoriza redistribuir los archivos .ttf**
  dentro de un repositorio de código, producto o dependencia interna reutilizable como
  `brand/`. Para ese tipo de redistribución (empresarial, en software, en servidores),
  Microsoft ofrece licenciamiento aparte que debe gestionarse directamente con ellos.
- Conclusión: **no se agregan los .ttf de Aptos a este repositorio** hasta que el cliente
  confirme que IH México ya cuenta con — o puede obtener — ese licenciamiento de redistribución
  empresarial de Microsoft. Sin esa confirmación explícita, redistribuir los archivos violaría
  los términos de uso estándar.

**Pregunta pendiente para el cliente:** ¿IH México tiene (o puede gestionar) un acuerdo de
licenciamiento con Microsoft que cubra la redistribución de los archivos de fuente Aptos dentro
de este repositorio? Si la respuesta es sí, compartir la confirmación/documento de licencia y
se agregarán los archivos `.ttf` y se actualizará `license_status` en
`brand/tokens/typography.yaml`.

Mientras se confirma, el sistema de tokens usa como fallback documentado:
`--ih-font-heading: Aptos, Arial, sans-serif;` — si Aptos no está disponible en el dispositivo
del usuario, el navegador/sistema usará Arial automáticamente. No se debe cargar Aptos desde
una fuente no autorizada (ej. repositorios de terceros en GitHub) sin validar la licencia.

Si el cliente confirma la licencia, colocar aquí los archivos originales de
`TYPEFACE-*.zip / TYPEFACE/Aptos/*.ttf` (11 pesos: Regular, Bold, Black, ExtraBold, SemiBold,
Light + itálicas) y actualizar `brand/tokens/typography.yaml` (`license_status`).
