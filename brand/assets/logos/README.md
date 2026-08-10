# Catálogo de logos — International House LATAM

Este directorio concentra los logos recuperables de la carpeta compartida de Drive para el
sistema LATAM. El catálogo no asume que todos los archivos representan la misma marca: cada
entrada de `manifest.yaml` indica `scope`, `brand`, `country` y la fuente original.

## Estructura

```text
logos/
├── classic/                         Compatibilidad con el catálogo inicial de IH México
├── black/                           Compatibilidad con el catálogo inicial de IH México
├── white/                           Compatibilidad con el catálogo inicial de IH México
├── white-reversed/                  Reservado: variante IH pendiente de fuente oficial
├── dual-branding/                   Reservado: lockup IH World + escuela pendiente
├── latam/
│   ├── colombia/{barranquilla,bogota,cali,medellin}/
│   ├── mexico/
│   ├── peru/lima/
│   └── chile/santiago/
├── global/ih-world/                 Logos globales de IH World
├── sub-brands/{hello-live,qc}/       Sub-marcas provistas por el cliente
└── partner-brands/{cambridge-english,ielts,michigan}/
```

## Estado actual

- 90 archivos registrados y aprobados en `manifest.yaml`: 4 activos originales de México, 74
  archivos recuperados desde Drive y 12 variantes PNG/JPG de Hello Live English.
- El catálogo incluye México, Colombia, Perú, Chile, IH World, Hello Live, QC, Cambridge English,
  IELTS y Michigan Language Assessment.
- Los activos `partner` están disponibles para composiciones de producto, pero no son logos IH y
  deben conservar las reglas del manual de su propietario. No se deben usar para sustituir el
  logo institucional.
- `white-reversed` y `dual-branding` siguen pendientes: los archivos disponibles no prueban que
  sean esas variantes oficiales.
- Hello Live English y Live English Kids cuentan con identidad visual propia adoptada el
  2026-08-09. Su paleta, tipografía, iconografía y estilo se documentan en
  `brand/documentation/sub-brands/hello-live-english.md`; no sustituyen el sistema institucional
  de IH.

## Elementos de Drive no incorporados como logos

1. `Cambridge/SVG` (`1-pT1Q2bgBKv2mYVbm5-G56Y9UGuoTk6L`): Drive devuelve error 500 al descargarlo;
   queda pendiente de recuperación.
2. `Cambridge/Logo-cambridge-platinum.png` (`1YAgATDArQIBFYPDTz8_UPKwKKL3_wan`): el enlace
   público devuelve 404; se conserva la versión JPG y la versión white PNG disponibles.
3. Los tres archivos `Michigan/24.1.Brandfolder-InfoCard-*.jpg` son hojas de referencia de
   Brandfolder, no artwork de logo; se excluyeron del catálogo de logos.

## Reglas de registro

Todo archivo de logo que se use desde el backend debe tener una entrada en `manifest.yaml` con
`approved: true`. Para un logo IH se usa `clear_space_rule: exclusion-zone-half-globe-diameter`.
Para una sub-marca o partner se usa `partner-brand-guidelines-required` hasta que su propio
manual se incorpore al repositorio; no se inventan reglas de uso.

El campo `approved` indica que el archivo fue provisto por el cliente para formar parte del
catálogo. `scope` evita confundir disponibilidad técnica con pertenencia a la identidad central:

| Scope | Uso |
| --- | --- |
| `regional` | Logos de una operación IH por país o ciudad |
| `global` | Logos de IH World |
| `sub-brand` | Hello Live y QC |
| `partner` | Cambridge, IELTS y Michigan |
| sin campo | Entradas heredadas del catálogo inicial de México |

## Cómo cargar un archivo nuevo

1. Colócalo en la carpeta de alcance correcto y conserva el formato original.
2. Registra el archivo en `manifest.yaml`, incluyendo `name`, `variant`, `format`, `file`,
   `allowed_backgrounds`, `clear_space_rule`, `approved`, `scope`, `brand`, `country` y la fuente.
3. No declares `white-reversed` ni `dual-branding` por parecido visual: requieren confirmación del
   artwork oficial.
4. Ejecuta las validaciones del repositorio antes de solicitar revisión.

Los tokens y archivos generados no se editan desde este directorio: `brand/tokens/colors.json` y
todo `brand/generated/*` solo se regeneran con `python brand/scripts/generate_tokens.py`.
