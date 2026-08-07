# Recomendación para el endpoint legacy de aprobación

Estado: recomendación; no implementado todavía.

## Recomendación

Mantener `POST /api/v1/designs/{id}/review/` como adaptador de compatibilidad temporal, pero no
usarlo como el flujo principal cuando `DESIGN_TEST_MODE` se desactive. El flujo principal debe ser
un servicio/panel formal de revisión que persista comentarios, usuario, versión revisada, decisión y
fecha.

## Flujo propuesto después del lote de 50

```text
self_review → claude-review: pass → in_review → approved
                                      ├→ revision_requested
                                      └→ rejected
```

`needs_changes` de Claude debe volver a `revision_requested` sin simular aprobación humana. La
aprobación humana debe requerir `reviewer` o `platform_admin`, una versión explícita y comentario
cuando la decisión sea rechazo o solicitud de cambios.

## Tratamiento del endpoint legacy

Cuando exista el panel formal:

1. Delegar la decisión al mismo servicio de dominio que usa el panel.
2. Rechazar acciones sin versión explícita.
3. Añadir una marca de deprecación y documentar la fecha de retiro.
4. Mantenerlo solo mientras existan clientes legacy; no duplicar reglas de transición en dos lugares.

No se implementa este cambio hasta que se confirme el diseño del panel formal y el responsable de
aprobar.
