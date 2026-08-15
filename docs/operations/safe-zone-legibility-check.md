# Diseño: safe-zone y legibilidad por `DesignVersion`

## Alcance

Cada `DesignVersion` nueva recibirá una comprobación determinista de zona segura y legibilidad.
La comprobación se ejecutará desde el mismo punto común que ya registra la creación de versiones,
para cubrir quick-design, generación por paquetes, revisión y cualquier futuro flujo que use el
modelo `DesignVersion`. No se crea un modelo ni un estado paralelo.

## Zonas seguras por formato social

Las plantillas sociales actuales (`square-v1`, `story-v1`, `portrait-v1`) reservan 72 px de margen
en un canvas de 1080 px de ancho. La política se expresa como porcentajes para que pueda aplicarse
si cambia la resolución:

| Formato | Canvas de referencia | Izquierda/derecha | Arriba/abajo | Motivo |
| --- | --- | ---: | ---: | --- |
| `square` | 1080 × 1080 | 6.67% | 6.67% | coincide con 72 px del template actual |
| `portrait` | 1080 × 1350 | 6.67% | 5.33% | conserva 72 px verticales del template actual |
| `story` | 1080 × 1920 | 6.67% | 3.75% | conserva 72 px verticales del template actual |

La política inicial verifica las regiones declaradas por el template contra esos límites; no
intenta inferir coordenadas desde una imagen raster. Si se incorporan overlays específicos de una
plataforma (por ejemplo, controles de Stories), se añadirá una versión de política explícita y se
actualizará este documento.

## Legibilidad y contraste

Se reutiliza el resumen de validación que ya produce el renderer y se interpreta contra
`brand/documentation/accessibility-rules.md`: texto normal requiere ratio mínimo 4.5:1 (AA), texto
grande puede usar 3:1 (AA18) solo cuando el layout lo declara como texto grande, y 7:1 corresponde
a AAA. En esta primera comprobación, cualquier par de texto normal por debajo de 4.5:1 marca
`needs_changes`; no se recalculan ni se inventan colores fuera de los tokens autorizados.

## Persistencia y comportamiento ante fallos

El resultado se guarda dentro de `DesignVersion.validation_summary["safe_zone_check"]`, junto con
las regiones evaluadas, porcentajes aplicados, resultado de contraste y mensajes accionables. Es la
misma superficie de validación que ya consume el panel; no se duplica en `Design` ni en
`claude_review`.

Una pieza se persiste para conservar trazabilidad incluso si el check falla. En ese caso el
resumen de validación queda en `needs_changes`, pero no se muta `claude_review_status` ni se fuerza
la transición de `Design`: esos estados pertenecen al flujo de revisión automática/humana existente.
El equipo debe corregir la versión antes de aprobarla. Formatos sin regiones sociales (A4, PPTX o
email) reciben `status=skipped` con motivo explícito; no se les aplica una zona social inventada.

## Pendientes

- Confirmar con cada plataforma social si se requieren overlays distintos a la reserva base de
  los templates.
- Añadir políticas específicas solo cuando exista el formato y la evidencia de sus dimensiones.
