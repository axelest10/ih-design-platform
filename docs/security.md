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

## Autenticación actual

DRF usa `SessionAuthentication`. `POST /api/v1/auth/login/` autentica cada cuenta mediante
`django.contrib.auth.authenticate`, verifica que su email pertenezca a un dominio autorizado y
establece una sesión individual. El endpoint limita intentos por IP a `10/hour` de forma
predeterminada; la tasa se puede cambiar con `LOGIN_THROTTLE_RATE`.

`GET /api/v1/health/` y el endpoint de login permanecen públicos; el resto de las superficies
protegidas conserva `CorporateDomainPermission` cuando `DJANGO_REQUIRE_CORPORATE_AUTH=1`.

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
