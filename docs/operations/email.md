# Correo transaccional con Postmark

IH Design usa Postmark como único proveedor soportado por el código nuevo. La aplicación web de
Production es `https://mydesign.ihlatam.com` y el remitente aprobado es
`IH Design <mydesign@ihlatam.com>`. El dominio verificado es `ihlatam.com`; no se necesita ni se
debe configurar `mydesign.ihlatam.com` como dominio de envío.

## Arquitectura y comportamiento

`backend/security/services/email.py` contiene el único cliente del proveedor y expone
`send_transactional_email`. Los flujos actuales son la recuperación de contraseña y la entrega
Celery del enlace autenticado de un diseño aprobado. Ambos conservan destinatario, asunto, HTML y
texto; la recuperación conserva además enlace en fragmento, caducidad, uso único y respuesta
genérica anti-enumeración.

El adaptador usa `POST https://api.postmarkapp.com/email` con
`X-Postmark-Server-Token`, HTML y texto, tags `password-reset` o `approved-design`, tracking
desactivado y el stream
transaccional configurado. Reply-To se omite cuando no está definido. Una respuesta aceptada debe
incluir `ErrorCode=0` y `MessageID`; el identificador se registra en un evento operativo seguro.
No se registran token del servidor, destinatario, contenido ni URL de recuperación.

Antes de llamar al proveedor se crea `TransactionalEmailDelivery`, sin asunto ni contenido, y su
ID interno viaja como metadata para poder asociar un webhook que llegue antes que la respuesta de
la API. `EmailRecipientState` conserva la supresión vigente y bloquea nuevos envíos locales a una
dirección suprimida. `PostmarkWebhookEvent` conserva una versión segura de Delivery, Bounce,
SpamComplaint y SubscriptionChange. Nunca se reenvía automáticamente un correo rebotado.

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
| `POSTMARK_WEBHOOK_USERNAME` | Usuario secreto de HTTP Basic, exclusivo del entorno. |
| `POSTMARK_WEBHOOK_PASSWORD` | Contraseña secreta de HTTP Basic, exclusiva del entorno. |
| `POSTMARK_WEBHOOK_MAX_BYTES` | Límite del request del webhook; `65536` por defecto. |
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

## Webhooks de estado del proveedor

El endpoint dedicado es `POST /api/v1/webhooks/postmark/`. Solo ese endpoint está exento de CSRF
y exige HTTP Basic antes de leer o procesar JSON. Si faltan credenciales devuelve 503; si la
autenticación no coincide devuelve 403; si el cuerpo excede el límite devuelve 413. Postmark no
ofrece firma HMAC de webhooks, por lo que se usa su `HttpAuth` soportado con credenciales distintas
por entorno:

- Staging: `https://mydesign-staging.ihlatam.com/api/v1/webhooks/postmark/`
- Production: `https://mydesign.ihlatam.com/api/v1/webhooks/postmark/`

En el servidor y stream `outbound` correspondiente se habilitan exclusivamente **Delivery**,
**Bounce**, **Spam complaint** y **Subscription change**. **Open** y **Click** permanecen apagados.
En Postmark se configura la URL HTTPS y `HttpAuth` con el usuario/contraseña que el propietario
ingresó directamente como `POSTMARK_WEBHOOK_USERNAME` y `POSTMARK_WEBHOOK_PASSWORD` en Railway del
mismo entorno. Las credenciales no se incluyen en la URL ni se copian entre Staging y Production.

Cada evento conocido se vincula por `MessageID` o, para la carrera inicial, por el ID interno de la
metadata. SubscriptionChange sin `MessageID` solo se acepta para un destinatario que ya tenga un
correo local. Un SHA-256 estable de la identidad del evento tiene restricción `unique`, por lo que
un retry recibe 200 sin duplicar el audit ni volver a mutar estado. Eventos desconocidos o de un
mensaje ajeno reciben 200 y se ignoran; payloads conocidos incompletos reciben 400. Se persisten
destinatario, timestamp, stream, clasificación y detalle saneado, pero se descartan asunto, HTML,
texto, `Content`, enlaces y tokens.

## Configuración y prueba segura de Staging

El propietario ingresa el token directamente en las variables Railway de Staging, junto con:

```text
EMAIL_DELIVERY_MODE=allowlist
EMAIL_ALLOWED_RECIPIENTS=<destinatario(s) de prueba aprobado(s)>
POSTMARK_FROM_EMAIL=mydesign@ihlatam.com
POSTMARK_FROM_NAME=IH Design
POSTMARK_MESSAGE_STREAM=outbound
POSTMARK_REPLY_TO=
POSTMARK_WEBHOOK_USERNAME=<ingresado directamente en Railway y Postmark Staging>
POSTMARK_WEBHOOK_PASSWORD=<ingresado directamente en Railway y Postmark Staging>
POSTMARK_WEBHOOK_MAX_BYTES=65536
```

Tras el redeploy de Staging, se solicita recuperación solo para una identidad sintética cuya
dirección esté en la allowlist. Se reconcilia el `MessageID` del evento operativo con la actividad
del servidor Postmark y se comprueba que el enlace use el origen de Staging. Nunca se imprimen el
token, el destinatario completo ni la URL de recuperación.

## Migración de Production y rollback

Las variables Resend de Production se conservan temporalmente durante este cutover, pero el código
Postmark no las lee. No se eliminan ni se revocan antes de verificar el deployment Postmark. La
secuencia segura es:

1. Aprobar un PR cuyo diff contra el `main` vigente sea exclusivamente Postmark/Pillow y su
   reconciliación con los flujos de correo actuales.
2. Ingresar directamente en Railway Production el token de **IH Design — Production**, remitente,
   nombre, stream, credenciales webhook separadas y `EMAIL_DELIVERY_MODE=live`. Si todavía no se
   pretende desplegar, la mutación debe usar
   explícitamente `skipDeploys: true` (o el equivalente documentado verificado en ese momento).
3. Promover manualmente el SHA exacto; confirmar que no existe trigger automático.
4. Verificar salud, login legacy y Hub SSO, y una recuperación controlada aprobada; reconciliar
   `MessageID` y webhook.
5. En un cambio posterior explícitamente autorizado, eliminar `RESEND_API_KEY` y
   `RESEND_FROM_EMAIL` con `skipDeploys: true` porque el código nuevo ya no los usa.
6. Solo después, el propietario del workspace Resend real revoca la clave Production expuesta y
   verifica que ya no sea utilizable.

Para rollback antes de retirar Resend, se vuelve al deployment anterior y se conservan sus
variables. Después de revocar Resend, el rollback seguro es a un SHA Postmark conocido como bueno;
no se restaura la clave comprometida. Toda rotación Postmark crea primero un token nuevo en el
servidor correcto, actualiza Railway, verifica aceptación y solo después elimina el anterior.

Referencias oficiales: [Email API](https://postmarkapp.com/developer/api/email-api),
[webhooks](https://postmarkapp.com/developer/webhooks/webhooks-overview) y
[Webhook API/HttpAuth](https://postmarkapp.com/developer/api/webhooks-api).
