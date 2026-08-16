# Plan de integración SSO con IH Hub

**Estado:** diseño acordado, no implementado.

**Alcance de este documento:** dejar definido el contrato y las decisiones para una futura
implementación de inicio de sesión desde `ihlatam.com` (IH Hub). Este documento no activa SSO,
no modifica el login local existente y no añade middleware, vistas, endpoints ni pruebas de SSO.

## Contexto confirmado

IH Hub usa NextAuth.js. Con una sesión real activa, `GET /api/auth/session` devuelve un campo
`apiToken` que es un JWT firmado con HS256. La muestra observada contiene:

- `sub`: identificador estable del usuario en Hub.
- `tenantId`: entidad o país del Hub, por ejemplo `tenant_ih_mexico`.
- `email`: correo del usuario.
- `exp`: expiración del token; en la muestra observada era aproximadamente un mes.

HS256 implica un secreto compartido: design-platform podrá verificar el token únicamente cuando
la persona que administra la autenticación del Hub entregue el secreto correcto. El precedente de
`reportes.ihlatam.com`, que usa una sola contraseña compartida para todo el equipo, no se adopta:
no identifica al usuario individualmente y no es el patrón de integración que buscamos.

## Decisión de transporte

### Entrada desde la UI del Hub

La primera navegación propuesta es:

```text
https://design-platform.example.com/login.html?sso=<apiToken>
```

Se elige un query param en la navegación inicial porque un enlace normal desde la UI del Hub no
puede añadir un header HTTP personalizado. Un header solo sería viable si hubiera un proxy o una
llamada servidor-a-servidor controlada por el Hub, contrato que no está confirmado.

El query param debe ser un transporte de bootstrap, no la sesión de design-platform. Cuando se
implemente:

1. El frontend leerá `sso` únicamente en la ruta de entrada.
2. Lo enviará una sola vez al futuro endpoint de intercambio por `POST` y cuerpo JSON, sobre HTTPS.
3. Limpiará inmediatamente la URL con `history.replaceState`, sin conservar el token en la barra,
   historial o enlaces posteriores.
4. El backend nunca escribirá el token crudo en logs, eventos, errores, analytics, cookies ni base
   de datos. La política de `Referrer-Policy` debe impedir que se reenvíe a terceros.
5. Tras validar, el backend creará la sesión Django normal. El `apiToken` no se usará como cookie
   de sesión ni se reenviará al navegador.

El nombre del futuro endpoint es orientativo —por ejemplo,
`POST /api/v1/auth/ihlatam/exchange/`— y no debe implementarse en esta fase.

## Validación futura del token

La implementación deberá fallar cerrada y seguir este orden:

1. Leer el secreto únicamente desde `IHLATAM_SSO_SECRET`. Si está vacío o ausente, la integración
   se considera deshabilitada y no se intenta validar con un valor por defecto.
2. Decodificar el JWT con una biblioteca JWT mantenida, usando exclusivamente `HS256` y el secreto
   configurado. No se debe aceptar el algoritmo indicado por el token sin una allowlist explícita.
3. Exigir y validar como mínimo `sub`, `tenantId`, `email` y `exp`. La firma debe verificarse antes
   de confiar en cualquiera de esos valores.
4. Rechazar tokens expirados según `exp`, tokens malformados, firmas incorrectas, claims ausentes
   o tipos de claim inesperados. No se debe ampliar artificialmente la expiración con tolerancias
   locales; cualquier clock skew permitido debe acordarse con quien mantiene el Hub.
5. Normalizar el email con la misma regla del login local —trim y casefold— y aplicar la allowlist
   de dominios corporativos existente. Un JWT firmado no debe saltarse esa política local.
6. Buscar o crear el usuario local por email reutilizando la lógica existente de magic-link/provisión
   de usuarios. La implementación debe extraer o llamar ese helper existente; no debe crear una
   segunda versión de normalización, allowlist, activación o asignación de cuenta.
7. Crear la sesión con el mecanismo de sesión Django que ya usa la plataforma. El SSO no debe
   crear contraseñas, sustituir el magic-link ni asignar roles administrativos por el contenido del
   JWT. Los roles locales siguen siendo responsabilidad de los grupos y administradores de
   design-platform, salvo que exista un acuerdo posterior y explícito con Hub.

No se debe exigir `iss` o `aud` hasta confirmar que NextAuth los emite de forma estable. Si el Hub
confirma esos claims, deben añadirse a la allowlist de validación antes de activar la integración.

## Comportamiento de fallback

El SSO es una vía adicional y no un reemplazo del acceso existente:

| Situación | Resultado esperado |
| --- | --- |
| No viene `sso` | Se muestra y funciona el magic-link existente, sin cambios. |
| `IHLATAM_SSO_SECRET` está vacío | SSO queda inactivo; continúa el magic-link existente. |
| Token inválido, malformado o con firma incorrecta | No se crea sesión ni usuario; se registra solo un motivo técnico sin token y se ofrece magic-link. |
| Token expirado | No se crea sesión ni usuario; se ofrece magic-link. |
| Claims incompletos o email no permitido | No se crea sesión ni usuario; se ofrece magic-link. |
| Usuario ya tiene una sesión válida y llega un SSO inválido | No se destruye la sesión existente; se rechaza únicamente el intento SSO. |

Las respuestas al navegador deben evitar revelar si falló la firma, el email o la existencia de una
cuenta. Los logs estructurados pueden distinguir motivos internos (`missing`, `expired`, `invalid`,
`disallowed_email`) sin incluir el JWT ni datos sensibles innecesarios.

## Identidad local y `tenantId`

El email sirve para enlazar con la cuenta local en la primera versión, pero `sub` es el identificador
estable del Hub y debe conservarse para auditoría y futuras reconciliaciones. La propuesta de modelo
para la implementación es una entidad de identidad externa asociada al usuario local, por ejemplo
`IHLatamIdentity`, con:

- `user`: usuario Django asociado.
- `provider`: valor fijo `ihlatam`.
- `hub_subject`: claim `sub`, único junto con `provider`.
- `tenant_id`: claim `tenantId` más recientemente validado.
- `last_seen_at`: fecha de la última validación correcta.

No se debe guardar el JWT completo. Si una pantalla necesita saber el tenant de la sesión actual,
puede copiar el `tenant_id` validado a un contexto de sesión Django; la autorización debe partir de
la identidad persistida y de reglas locales, no de un valor enviado por el navegador.

### Uso futuro de `tenantId`

`tenantId` será la clave para seleccionar la entidad/país y su marca en la expansión LATAM. Debe
existir un mapa centralizado y revisable, por ejemplo:

```text
tenant_ih_mexico  -> MX / International House México
tenant_ih_bogota  -> CO / International House Bogotá
```

Ese mapa debe controlar catálogo, logos, colores y acceso regional sin dispersar condiciones por
las vistas. Un `tenantId` desconocido no debe recibir una marca por defecto silenciosa: se debe
rechazar la selección regional o enviar a revisión, manteniendo disponible el fallback local según
la política acordada.

## Pendientes antes de implementar

La implementación queda bloqueada hasta que Axel confirme luz verde y se resuelvan estos puntos con
quien administra IH Hub:

1. Entrega segura de `IHLATAM_SSO_SECRET` y procedimiento de rotación/revocación. El secreto real
   nunca debe entrar a Git, tickets, capturas ni este documento.
2. Confirmación de la vigencia real de `exp`, reloj permitido, comportamiento de renovación y qué
   ocurre cuando se revoca una sesión de Hub antes de que expire el JWT.
3. Confirmación de claims estables adicionales, especialmente si se deben validar `iss` y `aud`.
4. Confirmación de los valores canónicos de `tenantId` y su mapa país/entidad/marca.
5. Confirmación de cómo IH Hub enlazará hacia design-platform en su UI: URL final, entorno,
   allowlist de redirect/origen, texto del enlace y comportamiento de logout. Esa coordinación vive
   fuera de este repositorio, pero es requisito de lanzamiento.
6. Confirmación de los dominios de email que Hub puede emitir y de la política para usuarios que
   existen en Hub pero aún no existen localmente.
7. Acuerdo sobre observabilidad, soporte y plan de rollback antes de activar la primera integración
   real basada en `apiToken`.

## Criterios de implementación posterior

El prompt de implementación deberá modificar el mínimo posible: añadir la dependencia JWT y la
configuración necesaria, extraer/reutilizar el helper de provisión del login existente, crear el
intercambio protegido y añadir pruebas unitarias/integración para firma, expiración, claims,
allowlist, creación/reutilización de usuario, tenant y todos los fallbacks. Hasta entonces, el único
efecto de este plan es documental.
