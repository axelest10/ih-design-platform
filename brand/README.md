# brand/ — Sistema de marca reutilizable de International House LATAM

Este directorio es la dependencia interna de marca de International House LATAM: la fuente única de verdad
para colores, tipografía, activos oficiales y reglas de diseño, pensada para reutilizarse en
cualquier proyecto futuro (este backend, un frontend, otra plataforma de diseño, etc.), no solo
en `ih-design-platform`. Los tokens institucionales mantienen la fuente documental existente;
los logos se catalogan por región, país, sub-marca y partner para que cada proyecto consuma el
activo correcto sin mezclar identidades.

**Regla general: nada en este sistema es inventado.** Todo valor, regla o cifra proviene de uno
de estos documentos fuente, analizados el 2026-08-05:

- `International House Brand Guidelines (1).pdf` — manual de marca oficial global (IH World).
- `IH_Mexico_Sistema_Diseno_Web.docx` — sistema de diseño web de México (fuente confirmada por
  el cliente para colores por pilar).
- `IH_BRANDING_MARCA.docx` — documento subido por el cliente el 2026-08-05, confirma y resuelve
  contradicciones de la fuente anterior.
- `IH_Sistema_Colores_v2.docx` — versión previa del sistema de diseño web (superada; ver
  `product-colors/authorized-colors.yaml -> alternate_sources_not_used`).
- `Color por producto.pdf` — mapeo de color por producto con nomenclatura alterna ("Live!",
  "UP"). Confirmado por el cliente el 2026-08-05: son alias comerciales de "Inglés General"
  ("Live!", ahora renombrado "Hello!") y "University Programmes" ("UP") — mismos colores
  institucionales, ver `product-colors/authorized-colors.yaml -> commercial_alias`.

Cuando una cifra o regla no aparece en ningún documento, se marca explícitamente como
`mx_extension`, `NOT_OFFICIAL_PENDING_BRAND_APPROVAL`, o con una nota "pendiente de
confirmación" — nunca se completa por inferencia.

## Estructura

```
brand/
├── ih-mexico.yaml              Metadatos generales de marca (ya existía; consumido por sync_brand_guideline)
├── tokens/                     Fuente única de tokens (colores, tipografía, espaciado, radios, sombras, motion)
├── product-colors/             Colores autorizados por pilar/producto de negocio
├── assets/                     Activos oficiales (logos LATAM, íconos, rainbows, ilustraciones, fotografía, fuentes)
├── generated/                  Artefactos generados (CSS, JS, preset de Tailwind) — NO editar a mano
├── documentation/              Reglas de marca en Markdown, listas para diseñadores/desarrolladores
└── scripts/generate_tokens.py  Único generador de brand/tokens/colors.json y brand/generated/*
```

## Cómo consumir este sistema

### Desde el backend Django (este repo)

```python
from branding.services import loader, validators

tokens = loader.load_all_tokens()               # todo el sistema de marca
flat_colors = loader.flat_color_map()            # {"knowledge": "#3B44B5", ...}
result = validators.validate_product_color("cambridge", "#923472")  # True
```

O vía API: `GET /api/v1/branding/tokens/`, `GET /api/v1/branding/validate-color/?hex=...`.
Para sincronizar el registro `BrandGuideline` (base de datos) desde estos archivos:
`python manage.py sync_brand_guideline`.

### Desde cualquier otro proyecto (frontend, otra plataforma)

- CSS: importar `brand/generated/ih-brand.css` (variables `:root` con prefijo `--ih-`).
- JS/TS: `import ihBrandTokens from "brand/generated/tokens.js"`.
- Tailwind: extender la config con `brand/generated/tailwind-preset.js`.
- API de logos LATAM: `GET /api/v1/branding/logos/` devuelve el catálogo aprobado. Admite los
  filtros `scope`, `country`, `brand` y `variant`.
- YAML/JSON crudo: `brand/tokens/*.yaml` y `brand/tokens/colors.json` para herramientas que no
  usan Node/Python.

**Nunca edites `brand/generated/*` ni `brand/tokens/colors.json` a mano.** Edita los YAML en
`brand/tokens/` y `brand/product-colors/`, luego corre:

```bash
python brand/scripts/generate_tokens.py          # regenera
python brand/scripts/generate_tokens.py --check  # falla si algo quedó desactualizado (usado en tests/CI)
```

## Estado de cada área

| Área | Estado |
| --- | --- |
| Paleta institucional (8 colores) | ✅ Aprobada, verificada contra el manual oficial |
| Colores por producto/pilar | ✅ Aprobada, confirmada por el cliente el 2026-08-05 |
| Rainbow institucional | ✅ Aprobada (versión oficial del PDF, sin la variante "Teal" rechazada) |
| Tipografía (tipos, escala, pesos) | ✅ Aprobada — Aptos NO se redistribuye (licencia estándar de Microsoft no lo permite; ver abajo) |
| Espaciado, radios, sombras, grid | ⚠️ Extensión de México, no viene del manual global |
| Motion/animación | ❌ No documentado en ninguna fuente — valores provisionales marcados como no oficiales |
| Logos | ⚠️ Catálogo LATAM cargado: 78 entradas aprobadas; faltan white-reversed y dual-branding IH |
| Tamaño mínimo de logo | ⚠️ No está en el manual — designado por extensión MX (`mx_designated`), pendiente de aprobación formal |
| Ratio de contraste | ✅ Encontrado (2026-08-05): matriz oficial en `documentation/accessibility-rules.md`, umbrales WCAG 2.1 |
| Iconos, rainbows, globos (SVG/PNG) | ✅ Extraídos y organizados con manifest |
| Fotografía oficial | ⏳ Solo reglas de estilo documentadas; sin banco de imágenes recibido |
| Fuente Open Sans | ✅ Incluida (licencia OFL) |
| Fuente Aptos | ❌ No incluida — licencia estándar de Microsoft restringe redistribución; requiere licenciamiento empresarial confirmado por el cliente |
| Alias "Hello!"/"UP" | ✅ Confirmados como alias de Inglés General/University Programmes (2026-08-05); usan los colores institucionales existentes, no una paleta propia |

## Ver también

- `documentation/` — reglas detalladas por categoría (logo, color, tipografía, imagery, layout,
  accesibilidad, do's & don'ts).
- `product-colors/README.md` — detalle del mapeo de colores por producto.
- `assets/logos/README.md` — catálogo LATAM, clasificación por alcance y procedimiento para cargar logos.
