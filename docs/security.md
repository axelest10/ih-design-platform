# Seguridad de acceso corporativo

La API está preparada para exigir autenticación corporativa y una allowlist de dominios exactos.
La restricción se aplica en el backend, después de que Django autentique al usuario; no se confía en
un email enviado por el navegador ni en un header `X-User-Email`.

## Configuración

En producción deben estar definidos:

```env
DJANGO_REQUIRE_CORPORATE_AUTH=1
CORPORATE_ALLOWED_EMAIL_DOMAINS=ihmexico.com,ihbogota.com,ihsantiago.cl,ihlima.com
RESEND_API_KEY=<secreto fuera de Git>
RESEND_FROM_EMAIL=International House <login@dominio-verificado-en-resend>
MAGIC_LINK_MAX_AGE_SECONDS=900
```

El dominio se compara exactamente. Por ejemplo, `persona@ihmexico.com` es válido, pero
`persona@sub.ihmexico.com` y `persona@fake-ihmexico.com` no lo son.

## Autenticación actual

DRF usa `SessionAuthentication`. El acceso sin contraseña se inicia con
`POST /api/v1/auth/magic-link/request/` y se confirma desde
`GET /api/v1/auth/magic-link/verify/?token=...`. El correo solo se envía a dominios permitidos y
el enlace firmado expira por defecto en 15 minutos. Para garantizar uso único entre procesos y
reinicios, la base guarda únicamente el hash del token y su fecha de consumo; nunca guarda el
token en texto claro. La verificación obtiene o crea el usuario y establece la sesión Django.

El envío está aislado en `security.services.ResendEmailClient`. Usa la API HTTP de Resend y puede
sustituirse por un fake en pruebas sin realizar llamadas de red. El dominio del remitente debe
estar verificado en Resend.

El endpoint `GET /api/v1/health/` permanece público para monitoreo. Los dos endpoints de magic
link también son públicos porque crean la sesión; todos los demás endpoints DRF usan
`CorporateDomainPermission` cuando `DJANGO_REQUIRE_CORPORATE_AUTH=1`.

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

Los usuarios creados mediante magic link no reciben un grupo automáticamente. Un administrador
debe asignarles uno de estos grupos de forma controlada. El backend sigue validando el dominio
aunque el usuario pertenezca a un grupo correcto.

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
