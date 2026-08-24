# Flujo end-to-end de briefs

## Configuración de staging para pruebas de Axel

El lote de primeras pruebas conserva su protección por defecto. Para probar el flujo completo
`brief → revisión → entrega` en staging, configura explícitamente:

```text
DJANGO_ENV=staging
DESIGN_TEST_MODE=1
DESIGN_TEST_ALLOW_HUMAN_APPROVAL=1
CELERY_TASK_ALWAYS_EAGER=0
```

`DESIGN_TEST_ALLOW_HUMAN_APPROVAL` solo funciona fuera de `production`; la aplicación falla al
arrancar si se intenta activar allí. Si la bandera es `0`, el endpoint de revisión devuelve `409`
y conserva el bloqueo de las primeras 50 pruebas.

## Pasos reales

1. Crear un `DesignBrief` con formato `square`, `story` o `portrait`.
2. Generar o editar `generated_prompt` y confirmar el brief. Ese campo contiene copy publicitario
   en texto plano; no es un prompt visual ni genera imágenes con IA.
3. La confirmación crea una `Design` y su primera `DesignVersion`. En staging distribuido, el
   frontend debe esperar el `task_id` de Celery hasta que termine.
4. Un usuario con rol `reviewer` o `platform_admin` aprueba o rechaza la versión desde
   `POST /api/v1/designs/{id}/review/`.
5. Al aprobar, se crea un registro `DesignDelivery` con `requested_by`, `recipient_email`, versión,
   estado y enlace de descarga. Celery envía el correo mediante el límite central Postmark de
   `backend/security/services/email.py` y crea un `TransactionalEmailDelivery` para reconciliar
   aceptación, Delivery, Bounce, SpamComplaint y SubscriptionChange sin persistir el contenido.

El enlace de entrega apunta al export autenticado de la versión (`svg`, `pdf` o `pptx`, según el
artefacto disponible). El correo no adjunta archivos y requiere que el solicitante inicie sesión
para descargarlo.

## Formatos disponibles

La API rechaza explícitamente `reel`, `carousel`, `banner`, `presentation`, `html` y `svg` al crear
un brief, con el mensaje `formato no disponible todavía`. Esos valores permanecen en el modelo para
no invalidar datos históricos y podrán habilitarse cuando exista un renderer de brief completo.
