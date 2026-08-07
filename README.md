# IH Design Platform

Base técnica del MVP de la plataforma interna de diseño para International House México.

La plataforma convierte un brief comercial en una pieza controlada para redes sociales o WhatsApp. El contenido comercial debe provenir del catálogo y de campañas autorizadas; la IA solamente propone copy, conceptos e indicaciones visuales. Logos, precios, fechas, CTA y demás información crítica se componen con plantillas controladas.

## Inicio rápido

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Salud de la API: `GET http://127.0.0.1:8000/api/v1/health/`.

## Sistema de marca (brand/)

`brand/` es la dependencia interna de marca de IH México: colores, tipografía, activos
oficiales y reglas de diseño en un formato reutilizable por cualquier proyecto (no solo este
backend). Ver [brand/README.md](brand/README.md) para el detalle completo.

```powershell
python brand/scripts/generate_tokens.py          # regenera CSS/JSON/JS/Tailwind desde los YAML fuente
python brand/scripts/generate_tokens.py --check  # falla si algo quedó desactualizado
python manage.py sync_brand_guideline            # sincroniza BrandGuideline (DB) desde brand/
```

El backend expone estos tokens vía `GET /api/v1/branding/tokens/` y valida colores vía
`GET /api/v1/branding/validate-color/?hex=...&pillar=...`. La lógica vive en
`backend/branding/services/` (`loader.py`, `validators.py`).

Los logotipos oficiales aún no se cargan — `brand/assets/logos/` tiene la estructura y el
manifest de validación preparados. Ver
[brand/assets/logos/README.md](brand/assets/logos/README.md).

## Comandos de calidad

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check
$env:DJANGO_TESTING = "1"
pytest
```

Para PostgreSQL, establece `DB_ENGINE=postgresql` y las variables `POSTGRES_*` descritas en `.env.example`. `docker compose -f infrastructure/docker-compose.yml up -d` levanta PostgreSQL y Redis.

Consulta [PROJECT.md](PROJECT.md), [docs/architecture.md](docs/architecture.md) y [ROADMAP.md](ROADMAP.md) para el alcance y las decisiones del MVP.
