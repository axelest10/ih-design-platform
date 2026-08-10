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
RESEND_API_KEY=<secreto fuera de Git>
RESEND_FROM_EMAIL=International House <login@dominio-verificado-en-resend>
MAGIC_LINK_MAX_AGE_SECONDS=900
DESIGN_TEST_MODE=1
DESIGN_TEST_LIMIT=50
CELERY_TASK_ALWAYS_EAGER=0
CORS_ALLOWED_ORIGINS=
```

El almacenamiento local de logos y referencias no debe considerarse persistente en un PaaS. Para
staging se debe configurar S3-compatible mediante `django-storages` antes de cargar activos reales.
La autenticación corporativa también requiere un proveedor de sesión/SSO; el código actual valida
el dominio y los roles una vez que existe un usuario autenticado, pero no implementa por sí solo el
login de Microsoft/Google.

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
3. Confirmar el proveedor de login corporativo y el dominio de staging.
4. Configurar almacenamiento S3-compatible para logos, referencias y futuras exportaciones.
5. Ejecutar migraciones, `check --deploy` y `tests/smoke_deployment.py` contra el dominio real
   antes de iniciar o reanudar el lote de pruebas.
6. Crear el primer usuario `platform_admin` de forma controlada.
7. Recién entonces iniciar el lote de 50 pruebas.
