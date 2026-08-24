# Seguridad de acceso corporativo

La API está preparada para exigir autenticación corporativa y una allowlist de dominios exactos.
La restricción se aplica en el backend, después de que Django autentique al usuario; no se confía en
un email enviado por el navegador ni en un header `X-User-Email`.

## Configuración

En producción deben estar definidos:

```env
DJANGO_REQUIRE_CORPORATE_AUTH=1
CORPORATE_ALLOWED_EMAIL_DOMAINS=ihmexico.com,ihbogota.com,ihsantiago.cl,ihlima.com
LOGIN_THROTTLE_RATE=10/hour
```

El dominio se compara exactamente. Por ejemplo, `persona@ihmexico.com` es válido, pero
`persona@sub.ihmexico.com` y `persona@fake-ihmexico.com` no lo son.

## SSO central con IH LATAM Hub (Staging)

Cuando `HUB_OIDC_ENABLED=1`, Design Platform actúa como cliente confidencial del proveedor OIDC
del Hub. Usa Authorization Code + PKCE S256, discovery/JWKS, firma RS256 y `state`/`nonce`.
El issuer y callback se configuran como URLs HTTPS exactas; nunca se derivan del `Host` recibido.
Los códigos duran 60 segundos en el proveedor y la sesión local de Design se limita a 15 minutos.
No se solicitan refresh tokens.

Al desactivar una identidad en el Hub se impiden nuevas autorizaciones inmediatamente. Una
sesión local de Design ya emitida no recibe una notificación global: su acceso termina, como
máximo, 900 segundos después del último login OIDC exitoso. Ese es el límite de revocación v1;
no se afirma logout global instantáneo.

El contrato de identidad permite solamente `sub`, `email`, `email_verified` y `name`. Design
rechaza claims de rol, centro, país, organización o tenant y mantiene toda autorización en grupos
locales de Django. En el primer acceso, enlaza una cuenta existente solo por email normalizado
exacto; si no existe, crea una cuenta con contraseña inutilizable y el rol `viewer`. A partir de
entonces, el `sub` estable del Hub es la clave primaria y un cambio de email no reasigna la
identidad. Colisiones, duplicados, cuentas inactivas y emails no verificados fallan cerrados.

`HubIdentity` conserva el enlace estable y `HubIdentityEvent` registra eventos append-only sin
tokens, códigos, cookies, secretos ni payloads completos. El acceso por SSO puede superar la
allowlist histórica de dominios solo si la sesión y el enlace OIDC persistido coinciden; las
sesiones de contraseña siguen sujetas a la allowlist.

Las rutas son `/api/v1/auth/hub/login/` y `/api/v1/auth/hub/callback/`. Los destinos `next` se
aceptan solo como rutas relativas locales. Logout termina la sesión local de Design; el cierre
global queda fuera del contrato v1.

La activación exige toda la configuración OIDC. Production además requiere
`HUB_OIDC_PRODUCTION_APPROVED=1`; esa aprobación no se configura durante el trabajo de Staging.

Authlib 1.7.2 está fijado como cliente OAuth/OIDC mantenido. Gestiona discovery, estado, nonce,
PKCE y el intercambio de código. La extensión local `StrictHubOAuth2App` conserva la validación
de claims de Authlib pero fija la verificación criptográfica a RS256 y refresca JWKS solo ante
un `kid` desconocido. Los requests de discovery/JWKS/token usan timeouts y los logs de Authlib
permanecen por encima de DEBUG para no exponer verificadores PKCE efímeros.

## Autenticación local de contingencia

DRF usa `SessionAuthentication`. El acceso local secundario mediante `POST /api/v1/auth/login/`
autentica cada cuenta mediante
`django.contrib.auth.authenticate`, verifica que su email pertenezca a un dominio autorizado y
establece una sesión individual. El endpoint limita intentos por IP a `10/hour` de forma
predeterminada; la tasa se puede cambiar con `LOGIN_THROTTLE_RATE`.

`GET /api/v1/health/` y el endpoint de login permanecen públicos; el resto de las superficies
protegidas conserva `CorporateDomainPermission` cuando `DJANGO_REQUIRE_CORPORATE_AUTH=1`.

La recuperación de acceso usa `POST /api/v1/auth/password-reset/request/` y
`POST /api/v1/auth/password-reset/confirm/`. El correo transaccional se entrega mediante el
adaptador central de Postmark; el token firmado
expira en 15 minutos por defecto, solo se puede consumir una vez y la base guarda únicamente su
hash SHA-256. El token viaja en el fragmento de `login.html`, por lo que no forma parte de la
solicitud HTTP ni de los logs del servidor web.

La respuesta de solicitud siempre es genérica, incluso cuando la cuenta no existe, el entorno
suprime la entrega o Postmark rechaza la solicitud. Staging solo permite destinatarios incluidos
explícitamente en `EMAIL_ALLOWED_RECIPIENTS`; una lista vacía falla cerrada. Los eventos
operativos conservan únicamente estado, categoría segura, usuario interno y el `MessageID` de
Postmark cuando existe. No registran destinatario, contenido, URL de recuperación ni token del
proveedor.

## Roles corporativos

Los roles se modelan con grupos nativos de Django y se crean con:

```powershell
python manage.py sync_corporate_roles
```

| Grupo | Permisos principales |
| --- | --- |
| `platform_admin` | Configuración, catálogo, diseños y revisiones |
| `marketing` | Catálogo comercial, campañas, briefs y diseños |
| `designer` | Briefs, diseños, previews y validaciones |
| `reviewer` | Validaciones y aprobación/rechazo de diseños |
| `viewer` | Consulta de información autorizada |

La migración de seguridad desactiva el usuario compartido histórico y crea la cuenta inicial de
Axel con `platform_admin`. Desde el panel, un administrador puede crear cuentas corporativas,
asignar roles y establecer contraseñas; estas siempre se guardan con el hasher de Django.

## Paneles y acceso regional

- `platform_admin` ve el panel administrador, gestiona el catálogo y tiene `regional_brand_access`.
- `marketing` y `designer` usan el panel de usuario para crear briefs y solicitar diseños.
- `viewer` conserva acceso de solo lectura.
- Un usuario normal solo recibe logos IH del país seleccionado. `IH LATAM` y logos globales
  requieren acceso regional y un activo oficial disponible.
- Los logos cargados por usuarios se guardan como `pending_catalog` y pueden reutilizarse por su
  creador en briefs posteriores; no reemplazan automáticamente un logo oficial.

## Desarrollo local

Para ejecutar temporalmente el MVP sin una sesión corporativa:

```env
DJANGO_REQUIRE_CORPORATE_AUTH=0
```

Esta excepción es solo para desarrollo local; nunca debe llegar a producción.
