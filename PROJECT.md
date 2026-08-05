# Proyecto

## Objetivo del MVP

Convertir una solicitud comercial en una pieza lista para revisión en uno de estos formatos: post cuadrado (1080 × 1080), historia (1080 × 1920) o post vertical (1080 × 1350).

## Límites

- No se inventan precios, fechas, promociones, sedes, teléfonos, contactos ni información académica.
- Solo se usan activos oficiales y diseños aprobados como referencias.
- La IA no genera logos ni texto crítico dentro de imágenes.
- OpenAI es el proveedor inicial detrás de una interfaz propia; no se incorpora Claude en este MVP.

## Módulos

| Módulo | Responsabilidad |
| --- | --- |
| `branding` | Guías, colores, tipografías y reglas institucionales |
| `catalog` | Productos y sedes con información autorizada |
| `campaigns` | Campañas, promociones y vigencias |
| `briefs` | Solicitudes guiadas y validación del contrato |
| `designs` | Diseños, versiones y estados de aprobación |
| `assets` | Logos y activos oficiales |
| `validations` | Ejecuciones y resultados de validación |
| `ai` | Contrato de proveedores y adaptador OpenAI |

## Criterio de éxito

El backend debe aceptar un brief válido, conservar el origen de los datos comerciales y dejar preparado el flujo de composición, validación, revisión y aprobación sin depender todavía de un editor visual ni de generación remota.
