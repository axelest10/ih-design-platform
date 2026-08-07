# Proyecto

## Objetivo del MVP

Convertir una solicitud comercial en una pieza lista para revisión en uno de estos formatos: post cuadrado (1080 × 1080), historia (1080 × 1920) o post vertical (1080 × 1350).

## Límites

- No se inventan precios, fechas, promociones, sedes, teléfonos, contactos ni información académica.
- Solo se usan activos oficiales y diseños aprobados como referencias.
- La IA no genera logos ni texto crítico dentro de imágenes.
- OpenAI es el proveedor inicial detrás de una interfaz propia para la generación dentro del backend.
- Claude participa en la curación de `brand/knowledge/` y en la revisión visual mediante `claude-review`,
  pero no funciona como proveedor de generación dentro de `AIProvider` ni del backend.

## Módulos

| Módulo | Responsabilidad |
| --- | --- |
| `branding` | Guías, colores, tipografías y reglas institucionales — consume `brand/` (ver abajo) vía `branding.services` |
| `catalog` | Productos y sedes con información autorizada |
| `campaigns` | Campañas, promociones y vigencias |
| `briefs` | Solicitudes guiadas y validación del contrato |
| `designs` | Diseños, versiones y estados de aprobación |
| `assets` | Logos y activos oficiales (registro en base de datos, `is_approved`) |
| `validations` | Ejecuciones y resultados de validación |
| `ai` | Contrato de proveedores y adaptador OpenAI |

## Sistema de marca (brand/)

`brand/` es la dependencia interna de marca de IH México (colores, tipografía, activos
oficiales y reglas de diseño), pensada para reutilizarse en cualquier proyecto futuro, no solo
en este backend. Es la fuente única de verdad; `branding.services.loader` la carga y
`branding.services.validators` valida colores/logos contra ella. Ver
[brand/README.md](brand/README.md) para el detalle completo y
[docs/architecture.md](docs/architecture.md) para cómo se integra con el resto del backend.

Reglas del sistema de marca:
- No se inventa ninguna regla, color ni cifra: todo proviene de los documentos fuente
  analizados (manual oficial IH World + documentos de México), citados en cada archivo.
- Donde una regla no está documentada en ninguna fuente (p. ej. tamaño mínimo del logo, motion/
  animación, licencia de Aptos), se marca explícitamente como pendiente — no se completa por
  inferencia.
- Los logotipos oficiales están pendientes de carga por el cliente; la estructura y validación
  ya están preparadas en `brand/assets/logos/`.

## Criterio de éxito

El backend debe aceptar un brief válido, conservar el origen de los datos comerciales y dejar preparado el flujo de composición, validación, revisión y aprobación sin depender todavía de un editor visual ni de generación remota.
