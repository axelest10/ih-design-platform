# Flujo de revisión y aprobación

Estado: implementado en `POST /api/v1/designs/{id}/review/`.

## Contrato implementado

El endpoint delega la transición a `backend/designs/services/review.py`. Persiste la decisión sobre
una `DesignVersion`, el usuario revisor y el comentario en `DesignReviewComment`. Los estados de
versión son `pending`, `approved`, `rejected` y `changes_requested`; el estado de `Design` se
mantiene sincronizado.

## Flujo propuesto después del lote de 50

```text
self_review → claude-review: pass → in_review → approved
                                      ├→ revision_requested
                                      └→ rejected
```

`needs_changes` de Claude debe volver a `revision_requested` sin simular aprobación humana. La
aprobación humana debe requerir `reviewer` o `platform_admin`, una versión explícita y comentario
cuando la decisión sea rechazo o solicitud de cambios.

## Tratamiento del endpoint y notificaciones futuras

El endpoint exige una versión explícita. `approve` acepta comentario opcional; `reject` y
`request_changes` exigen comentario. La función `notify_review_transition()` es un hook no-op para
conectar notificaciones en una fase posterior; esta implementación no envía mensajes.

El frontend/panel debe llamar a este endpoint y no duplicar reglas de transición. El modo de
pruebas mantiene el bloqueo temporal existente hasta completar el lote inicial.
