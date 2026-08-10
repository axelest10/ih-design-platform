# Seguridad de acceso corporativo

La API está preparada para exigir autenticación corporativa y una allowlist de dominios exactos.
La restricción se aplica en el backend, después de que Django autentique al usuario; no se confía en
un email enviado por el navegador ni en un header `X-User-Email`.

## Configuración

En producción deben estar definidos:

```env
DJANGO_REQUIRE_CORPORATE_AUTH=1
CORPORATE_ALLOWED_EMAIL_DOMAINS=ihmexico.com,ihbogota.com,ihsantiago.cl,ihlima.com
SITE_ACCESS_PASSWORD=<contraseña compartida larga, aleatoria y fuera de Git>
SITE_ACCESS_THROTTLE_RATE=10/hour
```

El dominio se compara exactamente. Por ejemplo, `persona@ihmexico.com` es válido, pero
`persona@sub.ihmexico.com` y `persona@fake-ihmexico.com` no lo son.

## Autenticación actual

DRF usa `SessionAuthentication`. `POST /api/v1/auth/site-access/` recibe la contraseña compartida,
la compara en tiempo constante contra `SITE_ACCESS_PASSWORD` y establece una sesión Django como el
usuario técnico `shared-access`. Ese usuario tiene contraseña Django inutilizable y pertenece a los
cinco grupos corporativos, por lo que toda persona que conoce la contraseña compartida obtiene
acceso completo sin identidad individual.

El endpoint limita intentos por IP a `10/hour` de forma predeterminada; la tasa se puede cambiar con
`SITE_ACCESS_THROTTLE_RATE`. Si `SITE_ACCESS_PASSWORD` está vacía, el endpoint responde `503` y no
abre una sesión. `GET /api/v1/health/` y el endpoint de acceso permanecen públicos; el resto de las
superficies protegidas conserva `CorporateDomainPermission` cuando
`DJANGO_REQUIRE_CORPORATE_AUTH=1`.

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

La migración de seguridad crea o actualiza el usuario compartido y le asigna los cinco grupos. El
backend sigue validando que su correo técnico use un dominio permitido. Las reglas de rol se
conservan para compatibilidad, aunque el acceso compartido reúne todas las capacidades.

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
