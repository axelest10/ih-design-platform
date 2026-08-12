# Preparación de despliegue

Estado actual: el staging de Railway está desplegado y su endpoint de salud fue confirmado el
2026-08-09. El repositorio conserva SQLite para desarrollo local;
`infrastructure/docker-compose.yml` levanta PostgreSQL y Redis para pruebas locales de la
arquitectura de servicios.

## Base técnica actual

- `backend/config/settings.py` acepta `DATABASE_URL` con PostgreSQL y conserva SQLite para local.
- `DJANGO_ENV=staging|production` obliga a definir `DJANGO_SECRET_KEY` real.
- `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ALLOWED_ORIGINS` son configurables por
  entorno. El frontend actual se sirve desde Django y funciona same-origin; no hay una dependencia
  de CORS instalada porque todavía no existe un frontend separado.
- `infrastructure/Dockerfile` es reutilizable como imagen de aplicación si el build context es la
  raíz del repositorio. `railway.json` fija `builder=DOCKERFILE`, la ruta
  `/infrastructure/Dockerfile`, la migración pre-deploy y el healthcheck. El Dockerfile define el
  `CMD` de Gunicorn y agrega `/app/backend` al `PYTHONPATH` para que `config.wsgi` sea importable
  dentro de la imagen.
- `infrastructure/docker-compose.yml` es local: no debe trasladarse literalmente como arquitectura
  de producción.

## Variables mínimas para staging

```text
DJANGO_ENV=staging
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<secreto generado fuera de Git>
DJANGO_ALLOWED_HOSTS=<dominio del servicio>
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
DJANGO_REQUIRE_CORPORATE_AUTH=1
CORPORATE_ALLOWED_EMAIL_DOMAINS=ihmexico.com,ihbogota.com,ihsantiago.cl,ihlima.com
CSRF_TRUSTED_ORIGINS=https://<dominio-del-servicio>
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SECURE_COOKIES=1
DJANGO_HSTS_SECONDS=31536000
AWS_STORAGE_BUCKET_NAME=<bucket>
AWS_S3_REGION_NAME=<región del bucket>
AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=<credencial fuera de Git>
AWS_SECRET_ACCESS_KEY=<secreto fuera de Git>
OPENAI_API_KEY=<secreto fuera de Git>
OPENAI_MODEL=gpt-4.1-mini
ANTHROPIC_API_KEY=<secreto creado en Claude Console>
ANTHROPIC_MODEL=<ID de modelo habilitado para la cuenta; no se fija en el código>
ANTHROPIC_TIMEOUT_SECONDS=45
RESEND_API_KEY=<API key secreta de Resend>
RESEND_FROM_EMAIL=<remitente verificado, por ejemplo Design Platform <acceso@dominio>>
PASSWORD_RESET_MAX_AGE_SECONDS=900
LOGIN_THROTTLE_RATE=10/hour
DESIGN_TEST_MODE=1
DESIGN_TEST_LIMIT=50
CELERY_TASK_ALWAYS_EAGER=0
CORS_ALLOWED_ORIGINS=
```

El almacenamiento local de logos y referencias no debe considerarse persistente en un PaaS. Para
staging se debe configurar S3-compatible mediante `django-storages` antes de cargar activos reales.
La autenticación actual no depende de un proveedor externo: cada integrante usa su cuenta y una
contraseña almacenada con el hasher de Django. Los administradores crean cuentas y restablecen
contraseñas desde el panel.

La revisión visual automática usa la Messages API de Anthropic cuando `ANTHROPIC_API_KEY` y
`ANTHROPIC_MODEL` están configuradas. Sin ambas variables, las piezas se conservan y quedan en
`pending` con `integration_status=needs_confirmation`; una falla del proveedor deja
`integration_status=provider_error` y tampoco revierte la versión generada. El timeout es
configurable y la clave nunca se persiste en el reporte.

## Comandos del servicio web

El comando de arranque es:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

Railway inyecta `PORT`; `8000` es únicamente el fallback local. El comando completo del
Dockerfile también fija un worker, timeout de 120 segundos y envía access/error logs a stdout.

Antes del primer arranque se debe ejecutar, como pre-deploy o job controlado:

```text
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Celery no está activo en el flujo actual. Si se habilita, necesita un worker separado conectado a
`REDIS_URL`; no se debe ejecutar dentro del mismo proceso Gunicorn.

## Comparativo corto

| Opción | Encaje con este repositorio | Ventajas | Costes/riesgos |
| --- | --- | --- | --- |
| Railway | Muy directo para un primer staging: servicio web desde Dockerfile + PostgreSQL y Redis administrados | Menor fricción operativa y variables internas simples | Hay que separar los servicios de Compose y configurar almacenamiento persistente; dependencia de plataforma |
| Render | Buen encaje para web Docker, pre-deploy de migraciones y futuro worker Celery | Servicios web/worker y datastores administrados en el mismo panel | El filesystem es efímero por defecto; algunas tareas pre-deploy dependen del tipo de servicio/plan |
| Fly.io | Adecuado si se necesita elegir región y controlar Machines/servicios | Más control de red, región y configuración de contenedores | Mayor carga operativa: regiones, volúmenes, Postgres/Redis y recuperación quedan más bajo responsabilidad del equipo |

Recomendación técnica para este proyecto: Railway o Render para el primer staging; Railway por la
menor fricción con el Dockerfile y los servicios administrados, Render si se prioriza separar con
claridad web, worker y comandos pre-deploy. Fly.io lo dejaría para una necesidad concreta de región
o control de infraestructura.

## Troubleshooting: healthcheck correcto pero dominio público sin respuesta

### Incidente de Railway del 2026-08-09

El primer despliegue de staging necesitó resolver tres problemas diferentes, en este orden:

1. Gunicorn escuchaba siempre en `8000`, aunque Railway inyecta un valor dinámico en `PORT`. Se
   corrigió en `infrastructure/Dockerfile` usando `${PORT:-8000}` (commit `a5f4f85`).
2. El healthcheck interno usa `Host: healthcheck.railway.app`; Django rechazaba ese hostname porque
   no estaba en `ALLOWED_HOSTS`. Se agregó como host técnico permitido en
   `backend/config/settings.py` (commit `a5f4f85`).
3. Después de esas correcciones, Railway marcaba el deploy como `ACTIVE`, pero el dominio público
   devolvía `502`. El dominio conservaba manualmente el target port `8000`, mientras el log del
   deploy mostraba `Listening at: http://0.0.0.0:8080`. El healthcheck podía llegar al puerto
   dinámico correcto, pero el proxy público seguía enviando tráfico a `8000`. Se corrigió en
   **Settings > Networking** actualizando el target port del dominio a `8080`; fue un cambio de
   configuración en Railway, no de código.

Señales que permiten reconocer esta combinación:

- el deploy aparece como `ACTIVE`, pero el dominio público responde `502`;
- los Network Logs públicos no muestran requests que alcancen la aplicación;
- el deploy log sí muestra a Gunicorn vivo y declara
  `Listening at: http://0.0.0.0:<puerto-real>`;
- el target port guardado en el dominio no coincide con `<puerto-real>`.

Para corregirlo, revisar el puerto reportado por Gunicorn en **cada deploy** y confirmar que el
target port de todos los dominios públicos apunta al mismo valor. No asumir que una configuración
manual anterior sigue sincronizada con el `PORT` asignado actualmente. Railway documenta este caso
en [Application Failed to Respond](https://docs.railway.com/networking/troubleshooting/application-failed-to-respond).

### Smoke test del despliegue real

`tests/smoke_deployment.py` es un script standalone porque depende de red y de un entorno real. Su
nombre evita que pytest lo recolecte como parte de la suite local/CI. No contiene dominios
hardcodeados: exige `SMOKE_TEST_BASE_URL`, solicita `/api/v1/health/` y comprueba status `200` y el
JSON exacto esperado.

PowerShell:

```powershell
$env:SMOKE_TEST_BASE_URL="https://ih-design-platform-production.up.railway.app"
python tests/smoke_deployment.py
```

Shell compatible con POSIX:

```bash
SMOKE_TEST_BASE_URL=https://ih-design-platform-production.up.railway.app \
  python tests/smoke_deployment.py
```

Resultado exitoso esperado:

```text
OK 200 https://<dominio>/api/v1/health/ {'status': 'ok', 'service': 'ih-design-platform'}
```

## Checklist antes de desplegar

1. Crear el proyecto y los servicios administrados de PostgreSQL/Redis en el proveedor elegido.
2. Configurar las variables anteriores fuera del repositorio.
3. Confirmar que la cuenta administradora inicial fue creada al migrar y cambiar su contraseña.
4. Configurar almacenamiento S3-compatible para logos, referencias y futuras exportaciones.
5. Ejecutar migraciones, `check --deploy` y `tests/smoke_deployment.py` contra el dominio real
   antes de iniciar o reanudar el lote de pruebas.
6. Probar que la cuenta administradora puede abrir el panel y crear una cuenta de equipo.
7. Recién entonces iniciar el lote de 50 pruebas.

## Invalidación de caché del frontend

El frontend se sirve desde Django con una política diferenciada para evitar que un deploy mezcle
HTML nuevo con JavaScript anterior:

- las respuestas HTML usan `Cache-Control: max-age=0, no-cache, must-revalidate`;
- las plantillas generan URLs de CSS, JavaScript y `brand/generated/` con una huella SHA-256 del
  contenido (`?v=<12 caracteres>`); cuando la huella coincide, esos archivos se sirven por un año
  con `immutable`;
- una URL de CSS/JS sin versión o con una versión incorrecta se revalida, por lo que enlaces
  antiguos no quedan congelados;
- los logos y demás archivos de `brand/assets/` conservan caché público de 24 horas y no se marcan
  como inmutables; la documentación de marca se revalida;
- los archivos subidos siguen su política propia del proxy de materiales (una hora) o del storage
  configurado.

La versión se calcula desde el contenido durante el render del HTML; no requiere actualizar una
constante manual ni configurar una variable adicional en Railway.

## Diagnóstico por correlation ID

Cada respuesta incluye `X-Request-ID`. Si el cliente envía un UUID válido en ese encabezado se
conserva; cualquier otro valor se reemplaza por un UUID generado por la aplicación. Los eventos se
escriben como JSON compacto en el logger `ih_design.operations` y pueden localizarse en los logs
del servicio web de Railway buscando ese `correlation_id`.

Eventos disponibles:

- `authentication.login` y `authentication.rate_limited`;
- `brief.created`;
- `design.version_created` y `design.version_export`;
- `visual_review.started` y `visual_review.completed`.

Solo se registran IDs, estado, proveedor, formato, template y duración. No se aceptan como campos
de logging contraseñas, API keys, tokens, cookies, contenido de prompts, archivos ni datos base64.
Para investigar un incidente: copia `X-Request-ID` desde Network en el navegador, busca ese UUID en
Railway y sigue los eventos cronológicamente; si hubo proveedor externo, revisa `provider`,
`duration_ms` y `status` sin necesitar inspeccionar el contenido privado de la pieza.
