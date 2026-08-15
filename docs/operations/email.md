# Correo transaccional con Postmark

IH Design usa Postmark como único proveedor soportado por el código nuevo. La aplicación web de
Production es `https://mydesign.ihlatam.com` y el remitente aprobado es
`IH Design <mydesign@ihlatam.com>`. El dominio verificado es `ihlatam.com`; no se necesita ni se
debe configurar `mydesign.ihlatam.com` como dominio de envío.

## Arquitectura y comportamiento

`backend/security/services/email.py` contiene el único cliente del proveedor y expone
`send_transactional_email`. El flujo actual de correo es exclusivamente la recuperación de
contraseña. Conserva destinatario, asunto, HTML, texto, enlace en fragmento, caducidad, uso único y
respuesta genérica anti-enumeración. No existen tareas Celery, correos administrativos,
notificaciones ni otros envíos activos.

El adaptador usa `POST https://api.postmarkapp.com/email` con
`X-Postmark-Server-Token`, HTML y texto, tag `password-reset`, tracking desactivado y el stream
transaccional configurado. Reply-To se omite cuando no está definido. Una respuesta aceptada debe
incluir `ErrorCode=0` y `MessageID`; el identificador se registra en un evento operativo seguro.
No se registran token del servidor, destinatario, contenido ni URL de recuperación.

No hay reintentos automáticos. Un timeout puede ocurrir después de que el proveedor acepte el
mensaje; repetir sin idempotencia podría generar dos correos. Los fallos se reducen a categorías
seguras (`configuration`, `provider_rejected`, `provider_unavailable` o `invalid_response`) y el
endpoint mantiene HTTP 202 genérico.

## Variables

| Variable | Uso |
| --- | --- |
| `POSTMARK_SERVER_TOKEN` | Token secreto del servidor Postmark del entorno. Nunca va en Git, logs o transcript. |
| `POSTMARK_FROM_EMAIL` | `mydesign@ihlatam.com`. |
| `POSTMARK_FROM_NAME` | `IH Design`. |
| `POSTMARK_MESSAGE_STREAM` | Stream transaccional; valor esperado `outbound`. |
| `POSTMARK_REPLY_TO` | Buzón Reply-To opcional; vacío mientras no exista uno aprobado. |
| `EMAIL_DELIVERY_MODE` | `disabled`, `allowlist` o `live`. |
| `EMAIL_ALLOWED_RECIPIENTS` | Lista exacta separada por comas, usada solo por `allowlist`. |

Los tokens de **IH Design — Staging** e **IH Design — Production** son distintos. No se copian
entre entornos y nunca se usa el token Postmark del Hub.

## Política por entorno

- Local/test: `disabled`; las pruebas sustituyen la red por fakes.
- Staging: `allowlist`; una lista vacía o un destinatario no autorizado falla cerrada sin llamar
  a Postmark. `live` se rechaza durante el arranque.
- Production: `live` para entrega transaccional normal después de una migración aprobada. Puede
  mantenerse `disabled` mientras se prepara el release, pero no debe declararse operativa la
  recuperación por correo en ese estado.

Postmark documenta `POSTMARK_API_TEST` para validar payloads sin entrega. Es útil como diagnóstico,
pero no demuestra que el servidor dedicado de Staging, su remitente o su reputación sean correctos.
La aceptación real necesita el token de **IH Design — Staging** y un destinatario de prueba
explícitamente aprobado; nunca se elige una dirección de empleado por conveniencia.

## Configuración y prueba segura de Staging

El propietario ingresa el token directamente en las variables Railway de Staging, junto con:

```text
EMAIL_DELIVERY_MODE=allowlist
EMAIL_ALLOWED_RECIPIENTS=<destinatario(s) de prueba aprobado(s)>
POSTMARK_FROM_EMAIL=mydesign@ihlatam.com
POSTMARK_FROM_NAME=IH Design
POSTMARK_MESSAGE_STREAM=outbound
POSTMARK_REPLY_TO=
```

Tras el redeploy de Staging, se solicita recuperación solo para una identidad sintética cuya
dirección esté en la allowlist. Se reconcilia el `MessageID` del evento operativo con la actividad
del servidor Postmark y se comprueba que el enlace use el origen de Staging. Nunca se imprimen el
token, el destinatario completo ni la URL de recuperación.

## Migración de Production y rollback

La aplicación Production actual todavía depende de Resend. No se elimina su variable antes de
desplegar código Postmark. La secuencia segura es:

1. Aprobar un PR provider-only basado en `main`, sin cambios SSO.
2. Ingresar directamente en Railway Production el token de **IH Design — Production**, remitente,
   nombre, stream y `EMAIL_DELIVERY_MODE=live`, manteniendo `HUB_OIDC_ENABLED` apagado.
3. Promover manualmente el SHA provider-only exacto; confirmar que no existe trigger automático.
4. Verificar salud, login legacy y una recuperación controlada aprobada; reconciliar `MessageID`.
5. Eliminar `RESEND_API_KEY` y `RESEND_FROM_EMAIL` de Railway porque el nuevo código ya no los usa.
6. El propietario del workspace Resend real revoca la clave Production expuesta y verifica que ya
   no sea utilizable.

Para rollback antes de retirar Resend, se vuelve al deployment anterior y se conservan sus
variables. Después de revocar Resend, el rollback seguro es a un SHA Postmark conocido como bueno;
no se restaura la clave comprometida. Toda rotación Postmark crea primero un token nuevo en el
servidor correcto, actualiza Railway, verifica aceptación y solo después elimina el anterior.

Referencias oficiales: [Email API](https://postmarkapp.com/developer/api/email-api) y
[API overview/error handling](https://postmarkapp.com/developer/api/overview).
