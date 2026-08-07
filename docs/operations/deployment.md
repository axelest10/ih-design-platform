# Preparación de despliegue

Estado actual: no hay un entorno desplegado. El repositorio sigue operando localmente con
SQLite; `infrastructure/docker-compose.yml` levanta PostgreSQL y Redis para desarrollo. Esta
guía deja preparada la configuración, pero no crea cuentas ni despliega servicios.

## Base técnica actual

- `backend/config/settings.py` acepta `DATABASE_URL` con PostgreSQL y conserva SQLite para local.
- `DJANGO_ENV=staging|production` obliga a definir `DJANGO_SECRET_KEY` real.
- `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ALLOWED_ORIGINS` son configurables por
  entorno. El frontend actual se sirve desde Django y funciona same-origin; no hay una dependencia
  de CORS instalada porque todavía no existe un frontend separado.
- `infrastructure/Dockerfile` es reutilizable como imagen de aplicación si el build context es la
  raíz del repositorio y el proveedor recibe esa ruta de Dockerfile. No es un entorno de producción
  completo por sí solo.
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
```

El almacenamiento local de logos y referencias no debe considerarse persistente en un PaaS. Para
staging se debe configurar S3-compatible mediante `django-storages` antes de cargar activos reales.
La autenticación corporativa también requiere un proveedor de sesión/SSO; el código actual valida
el dominio y los roles una vez que existe un usuario autenticado, pero no implementa por sí solo el
login de Microsoft/Google.

## Comandos del servicio web

El comando de arranque es:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

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

## Checklist antes de desplegar

1. Crear el proyecto y los servicios administrados de PostgreSQL/Redis en el proveedor elegido.
2. Configurar las variables anteriores fuera del repositorio.
3. Confirmar el proveedor de login corporativo y el dominio de staging.
4. Configurar almacenamiento S3-compatible para logos, referencias y futuras exportaciones.
5. Ejecutar migraciones, `check --deploy` y smoke tests contra `/api/v1/health/`.
6. Crear el primer usuario `platform_admin` de forma controlada.
7. Recién entonces iniciar el lote de 50 pruebas.
