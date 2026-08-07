# Handoff: sistema de marca `brand/` en `ih-design-platform`

Contexto para pegar en Codex (u otra herramienta) — resume exactamente qué se hizo, qué
decisiones ya están tomadas y qué falta. Repo: `ih-design-platform` (rama `main`, sin commit ni
push todavía — todo queda como cambios locales sin confirmar).

## 1. Objetivo de la tarea

### Actualización 2026-08-06: ampliación a LATAM

La carpeta compartida de Drive se revisó completa y se incorporaron al repositorio 74 archivos
recuperables de logos regionales, globales, sub-marcas y partners. Sumados a los 4 activos de
México ya existentes, `brand/assets/logos/manifest.yaml` contiene 78 entradas aprobadas. La
clasificación por `scope`, país y marca evita tratar Cambridge, IELTS, Michigan, Hello Live o QC
como si fueran el logo institucional de IH. El detalle y los dos archivos de Drive no recuperables
están documentados en `brand/assets/logos/README.md`.

Esta actualización reemplaza el alcance exclusivamente México descrito en la sección 6; las
decisiones de colores, tipografía y variantes `white-reversed`/`dual-branding` no cambian.

Convertir los manuales de marca de International House México en una dependencia interna de
marca reutilizable (`brand/`), consumible desde este backend y desde futuros proyectos.

**Actualización 2026-08-05 (segunda pasada):** se cargaron los logotipos oficiales — variantes
`classic`, `black` y `white` — a partir de una carpeta local del cliente y confirmadas contra
una carpeta de Google Drive que el cliente compartió. Faltan `white-reversed` y
`dual-branding`. Ver sección 6 actualizada.

**Actualización 2026-08-05 (tercera pasada):** se resolvieron 3 de las 4 preguntas pendientes
de la sección 7 (ratio de contraste, licencia de Aptos, tamaño mínimo de logo) y se confirmaron
los alias "Live!"/"Hello!" y "UP". Ver sección 7 actualizada — solo queda pendiente el logo de
`white-reversed`/`dual-branding` y la confirmación de licenciamiento empresarial de Aptos.

## 2. Documentos fuente analizados

- `International House Brand Guidelines (1).pdf` — manual oficial global (IH World). Fuente
  principal de: paleta de 8 colores, tipografía (Aptos/Open Sans), reglas de logo, fotografía,
  iconografía, rainbow.
- `IH_Mexico_Sistema_Diseno_Web.docx` — sistema de diseño web de México. Fuente de: colores por
  pilar/producto, escala tipográfica detallada, grid, espaciado, componentes web.
- `IH_Sistema_Colores_v2.docx` — versión previa del sistema de diseño web. **Descartada como
  fuente de colores por producto** (divergía en 4 pilares).
- `Color por producto.pdf` — mapeo de color por producto con nombres alternos ("Live!", "UP").
  **No usado como fuente principal** — nombres sin confirmar.
- `IH_BRANDING_MARCA.docx` — documento que el usuario subió a media tarea. Confirma que
  `IH_Mexico_Sistema_Diseno_Web.docx` es la fuente correcta y resuelve las contradicciones entre
  los dos docx de México.

## 3. Decisiones ya confirmadas por el cliente (2026-08-05) — NO volver a preguntar

1. **Fuente de colores por producto/pilar:** `IH_Mexico_Sistema_Diseno_Web.docx` /
   `IH_BRANDING_MARCA.docx` (coinciden exactamente). `IH_Sistema_Colores_v2.docx` y
   `Color por producto.pdf` quedan como referencia descartada.
2. **Rojo IELTS oficial:** `#E31736` (no `#e41836` del PDF de producto, ni `#C0392B` de la
   variante de overlay de hero).
3. **Rainbow institucional:** versión del manual oficial (8 colores, incluye Light Orange
   `#F4AB63`). Se rechazó una variante de un docx de México que sustituía ese color por un
   "Teal" `#407B98` inexistente en cualquier paleta oficial.
4. **Divergencia entre los dos docx de México** (Cambridge, University, Empresas, IELTS):
   resuelta a favor de `IH_Mexico_Sistema_Diseno_Web.docx` (confirmado también por
   `IH_BRANDING_MARCA.docx`).

Los 8 colores institucionales base coinciden exactamente entre el manual oficial y la lista que
dio el cliente al inicio — no hubo contradicción ahí:

| Nombre | Token | HEX |
| --- | --- | --- |
| Knowledge Blue | `knowledge` | `#3B44B5` |
| Technology Purple | `technology` | `#923472` |
| Youth Green | `youth` | `#B7DB6E` |
| Joy Yellow | `joy` | `#F4CF80` |
| Light Orange | `light` | `#F4AB63` |
| Salmon | `salmon` | `#F06C6A` |
| Pink | `pink` | `#E070A2` |
| Green | `green` | `#28AE62` |
| Rojo IELTS (extensión MX confirmada) | `ielts_red` | `#E31736` |

Colores por pilar (principal): Inglés General `#B7DB6E`, Cambridge `#923472`, University
Programmes `#3B44B5`, Empresas `#28AE62`, IELTS `#E31736`, Spanish Courses `#F4AB63`. Detalle
completo (secundario, fondo, CTA, justificación) en
`brand/product-colors/authorized-colors.yaml`.

## 4. Estructura creada

```
brand/
├── ih-mexico.yaml                  (ya existía, sin cambios)
├── README.md                       Índice general del sistema de marca
├── tokens/
│   ├── colors.yaml                 Fuente única de colores (con cita de fuente por valor)
│   ├── colors.json                 GENERADO — no editar a mano
│   ├── typography.yaml
│   ├── spacing.yaml
│   ├── radius.yaml
│   ├── shadows.yaml
│   └── motion.yaml                 NO oficial — status: NOT_OFFICIAL_PENDING_BRAND_APPROVAL
├── product-colors/
│   ├── README.md
│   └── authorized-colors.yaml      Colores por pilar, confirmados por el cliente
├── assets/
│   ├── logos/                      Carga parcial — ver sección 6
│   │   ├── manifest.yaml
│   │   ├── README.md
│   │   └── classic/ black/ white/ white-reversed/ dual-branding/
│   ├── icons/                      6 íconos oficiales (svg+png) + manifest.yaml
│   ├── rainbows/                   5 variantes oficiales (svg+png) + manifest.yaml
│   ├── illustrations/globes/       4 variantes del globo IH (svg+png) + manifest.yaml
│   ├── photography/                README (sin material recibido aún)
│   └── fonts/
│       ├── open-sans/              .ttf + OFL.txt (licencia libre, incluida)
│       └── README.md               Aptos NO incluida — licencia estándar no permite redistribución
├── generated/
│   ├── ih-brand.css                GENERADO — variables :root --ih-*
│   ├── tokens.js                   GENERADO — export ihBrandTokens
│   └── tailwind-preset.js          GENERADO — preset de Tailwind
├── documentation/
│   ├── logo-rules.md
│   ├── color-rules.md
│   ├── typography-rules.md
│   ├── imagery-rules.md
│   ├── layout-rules.md
│   ├── accessibility-rules.md
│   └── do-and-dont.md
└── scripts/
    └── generate_tokens.py          Único generador de colors.json + generated/*
```

```
backend/branding/
├── services/
│   ├── loader.py         Carga y cachea los YAML de brand/ (functools.cache)
│   └── validators.py     valida HEX, color autorizado, color por pilar, logo aprobado,
│                          detecta tokens contradictorios (find_duplicate_token_conflicts)
├── management/commands/
│   └── sync_brand_guideline.py   Sincroniza el modelo BrandGuideline (DB) desde brand/
└── views.py       (modificado) + brand_tokens y validate_color (nuevas vistas)
```

```
tests/
├── test_branding_tokens.py   formato HEX, colores oficiales, pilares, sin duplicados
│                              contradictorios, rainbow correcto, motion no oficial,
│                              generated/* sincronizados con YAML (subprocess --check)
├── test_branding_assets.py   manifests de iconos/rainbows/globos, archivos existen en
│                              disco, logo no registrado se rechaza, logo approved=false
│                              se rechaza, fuentes (Open Sans sí / Aptos no) presentes
└── test_branding_api.py      /api/v1/branding/tokens/, /api/v1/branding/validate-color/,
                               management command sync_brand_guideline, API de BrandGuideline
```

Endpoints nuevos (además del CRUD existente `/api/v1/branding/`):

- `GET /api/v1/branding/tokens/` — todo el árbol de tokens en JSON.
- `GET /api/v1/branding/validate-color/?hex=#3B44B5&pillar=cambridge` — valida un color.

Comando nuevo: `python manage.py sync_brand_guideline` (upsert del `BrandGuideline` en DB desde
`brand/`).

Regla de oro del sistema: **`brand/tokens/colors.json` y todo `brand/generated/*` se generan**
con `python brand/scripts/generate_tokens.py` — nunca se editan a mano. Hay un modo
`--check` (usado en `tests/test_branding_tokens.py`) que falla si algo quedó desincronizado.

## 5. Validaciones ejecutadas — todas en verde (última corrida: tercera pasada, 2026-08-05)

- `ruff check .` → **All checks passed!**
- `python manage.py check` → **System check identified no issues.**
- `python manage.py makemigrations --check --dry-run` → **No changes detected.**
- `pytest` (44 pruebas de branding + preexistentes) → **44 passed** (ejecutado sobre una copia
  limpia del repo por el problema de permisos descrito abajo; ver detalle).
- `git diff --check` → limpio para todo lo nuevo. Solo señala los archivos de migración
  (`backend/*/migrations/0001_initial.py`) que **ya estaban modificados antes de que empezara
  esta tarea** (aparecían en `git status` desde el primer comando que corrí) — parece un
  problema preexistente de saltos de línea (CRLF), no algo que yo haya tocado.

### Quirks del entorno (no relacionados con el código)

- `.git/index.lock` en el repo estuvo bloqueado con permisos que ni el propio `git` ni `rm -f`
  pudieron liberar (`Operation not permitted`) en mi entorno — impidió `git add`/`git commit`
  desde ahí. No debería afectarte en tu máquina/Codex si el lock no existe ahí.
- `.pytest_cache/` dentro del repo tiene permisos que bloquean a pytest al arrancar
  (`PermissionError`) en mi entorno. Workaround usado: correr pytest sobre una copia temporal
  del repo (`rsync` excluyendo `.git`, `.pytest_cache`, `.ruff_cache`, `__pycache__`,
  `db.sqlite3`). Puede que en tu entorno este directorio ya no tenga ese problema.
- Se agregó `db.sqlite3-journal` a `.gitignore` (quedó un archivo journal suelto de una corrida
  de `manage.py` que falló por I/O del filesystem montado).

## 6. Logos — histórico de carga inicial (superado por la actualización LATAM)

Los párrafos siguientes documentan la primera carga de México del 2026-08-05. Para el estado
vigente y el catálogo completo debe consultarse `brand/assets/logos/manifest.yaml` y
`brand/assets/logos/README.md`.

`brand/assets/logos/` ya tiene 3 de las 5 variantes esperadas cargadas y aprobadas:

| Variante | Archivo | Formato |
| --- | --- | --- |
| classic | `classic/ih-mexico-classic.png` (1089×340) | PNG |
| classic | `classic/ih-mexico-classic.ai` | AI (vectorial) |
| black | `black/ih-mexico-black.png` (1089×372) | PNG |
| white | `white/ih-mexico-white.png` (1089×372) | PNG |

Origen: una carpeta local que el cliente ya tenía en su máquina ("Logotipos IH MX Y QC"),
confirmada como equivalente a una carpeta de Google Drive que el cliente compartió
(`https://drive.google.com/drive/folders/14TZxcHMkSnnwWfwSk6fmxI2Ck1aZ9FeM` → subcarpeta
"Ih México", que solo tenía 2 exportaciones casi idénticas del color, sin negro/blanco/vector).
Registrados en `manifest.yaml -> logos:` con `approved: true` y notas de origen/fecha.

**Aviso para quien retome esto en Codex:** otras subcarpetas de esa misma unidad de Drive (p.
ej. "Cambridge") contienen el logo de certificación *Cambridge English Qualifications* (CEQ) —
un activo de un dominio distinto (insignia de acreditación externa), no confundir con el
logotipo institucional de IH México.

Falta cargar `white-reversed` y `dual-branding` — se investigó a fondo (carpeta local del
cliente + Drive compartido completo, incluida la subcarpeta "Hello Live" y "Hello Live
Pictures") y no se encontró fuente para ninguna de las dos. Procedimiento (en
`brand/assets/logos/README.md`):

1. Colocar cada archivo en su subcarpeta (`white-reversed/`, `dual-branding/`).
2. Registrar cada archivo en `manifest.yaml -> logos:` con todos los campos del `schema`
   (`approved: true` obligatorio).
3. Un logo en disco pero no registrado con `approved: true` es rechazado automáticamente por
   `backend/branding/services/validators.py::validate_logo` (hay tests que lo cubren:
   `tests/test_branding_assets.py`).

También sería deseable obtener versiones **SVG** de las 3 variantes ya cargadas (solo se
recibió PNG + un AI) — el AI no se puede leer/validar mediante herramientas de código abierto
sin conversión previa.

## 7. Preguntas pendientes — actualizado 2026-08-05 (tercera pasada)

1. **Licencia de Aptos — RESUELTO (parcialmente).** Microsoft sí publica una descarga oficial
   gratuita (`microsoft.com/en-us/download/details.aspx?id=106087`), pero la licencia estándar
   solo permite *usar* la fuente, no *redistribuir* los `.ttf` en un repositorio/dependencia
   interna — eso requiere licenciamiento empresarial aparte con Microsoft. **No se agregaron
   los `.ttf`.** `license_status` en `brand/tokens/typography.yaml` pasó de `UNKNOWN` a
   `RESTRICTED_STANDARD_LICENSE`. Fallback sigue siendo `Aptos, Arial, sans-serif`. Pendiente
   real: confirmar si IH México ya tiene (o puede gestionar) ese licenciamiento empresarial.
2. **Tamaño mínimo de logo — RESUELTO (designado, no oficial).** Se confirmó visualmente
   (render 150dpi de la página "Logo Size") que el manual no trae ninguna cifra numérica. Se
   designó un mínimo derivado de reglas ya documentadas (zona de exclusión, regla de video al
   30% del ancho de pantalla, legibilidad): 24px/10mm (isotipo solo), 32px/15mm (isotipo +
   wordmark), 48px/20mm (lockup completo con texto secundario). Documentado en
   `brand/documentation/logo-rules.md` con `status: mx_designated` — pendiente de aprobación
   formal del cliente/Marketing, no se presenta como cifra oficial del manual.
3. **Nombres "Live!"/"Hello!" y "UP" — RESUELTO.** Confirmado por el cliente: "Live!" (ahora
   "Hello!") = pilar "Inglés General"; "UP" = "University Programmes". Ambos son alias
   comerciales del mismo pilar/color institucional, documentados en
   `brand/product-colors/authorized-colors.yaml` (`commercial_alias` en cada pilar). **Ojo:**
   existe un deck interno ("Hello Live English — Presentación Directores") que describe a
   "Hello Live English" con identidad visual propia (paleta Navy/Cian/Verde/Naranja/
   Magenta/Morado, logo de burbuja de chat, tipografía Poppins, dominio
   helloliveenglish.com) — el cliente decidió explícitamente NO adoptar esa identidad aquí;
   "Hello!" usa el color y logo institucionales de siempre. No se encontró ningún archivo de
   logo de Hello en el Drive compartido (la carpeta "Hello Live" está vacía).
4. **Ratio de contraste WCAG oficial — RESUELTO, sí existe.** La página "Contrast and
   Accessible Colours" del manual SÍ trae una matriz oficial completa (10 colores × 10,
   niveles AAA ≥7:1 / AA ≥4.5:1 / AA18 texto grande ≥3:1 / DNP <3:1 — idéntico a WCAG 2.1). No
   se había detectado antes porque está renderizada como imagen/tabla, no como texto plano
   (`pdftotext` no la capturaba). Transcrita completa en
   `brand/documentation/accessibility-rules.md`. `brand/tokens/colors.yaml ->
   contrast_and_accessibility` pasó de `mx_extension_not_in_global_manual` a `approved`.

## 8. Qué le falta hacer a quien retome esto (para Codex)

- Cargar las variantes de logo que faltan (`white-reversed`, `dual-branding`) siguiendo el
  procedimiento de la sección 6. Ya se investigó a fondo en Drive y no se encontró fuente para
  ninguna de las dos — probablemente haya que pedírselas directamente al cliente/IH World.
- Si es posible, conseguir versiones **SVG** de las 3 variantes ya cargadas (hoy solo hay
  PNG + un `.ai` para `classic`).
- Confirmar con el cliente si IH México tiene licenciamiento empresarial de Microsoft para
  Aptos; si sí, copiar los `.ttf` desde
  `TYPEFACE-20260508T214822Z-3-001.zip / TYPEFACE/Aptos/*.ttf` a `brand/assets/fonts/aptos/` y
  actualizar `license_status` en `brand/tokens/typography.yaml` (hay un test que falla a
  propósito si se agregan `.ttf` de Aptos sin ese cambio:
  `test_aptos_font_files_are_not_redistributed_without_confirmed_license`).
- Conseguir aprobación formal (o corrección) del tamaño mínimo de logo `mx_designated` en
  `brand/documentation/logo-rules.md`.
- Revisar/aprobar formalmente `brand/tokens/motion.yaml` (actualmente marcado como
  `NOT_OFFICIAL_PENDING_BRAND_APPROVAL`, valores provisionales inventados con convenciones
  estándar de UI, no de marca).
- Fotografía oficial: `brand/assets/photography/` está vacía, solo con reglas de estilo — falta
  recibir banco de imágenes real.
- No se ha hecho `git add`/`commit`/`push` — todo sigue como cambios locales sin confirmar en
  `main`.

## 9. Biblioteca de artes de referencia — actualización 2026-08-06

Se revisó la carpeta compartida de Drive organizada por país:
`https://drive.google.com/drive/folders/1JHqf-eHT1kScVyz7bJ-d2Fn2wQ6TdJX4`.

- Se encontraron 35 carpetas y 454 archivos: 314 imágenes y 140 videos.
- Se copiaron las 314 imágenes en `brand/assets/artwork-references/{country}/`.
- Los 140 videos quedaron catalogados con su enlace de Drive, sin copiar binarios grandes.
- El inventario completo y la procedencia están en `brand/assets/artwork-references/manifest.yaml`.
- Todas las entradas son `reference_type: inspiration` y `approval_status: pending`; no se
  inventaron reglas de marca ni se aprobó material automáticamente.
- El modelo `ArtworkReference` ahora conserva `repository_path`, además de los enlaces de
  Drive. La sincronización se ejecuta con `python manage.py sync_artwork_references` y es
  idempotente sin sobrescribir aprobaciones existentes.
- Validación posterior: 61 tests, Ruff, `manage.py check` y `makemigrations --check` en verde.
