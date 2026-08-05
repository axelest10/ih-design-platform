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

## Comandos de calidad

```powershell
ruff check .
python manage.py check
$env:DJANGO_TESTING = "1"
pytest
```

Para PostgreSQL, establece `DB_ENGINE=postgresql` y las variables `POSTGRES_*` descritas en `.env.example`. `docker compose -f infrastructure/docker-compose.yml up -d` levanta PostgreSQL y Redis.

Consulta [PROJECT.md](PROJECT.md), [docs/architecture.md](docs/architecture.md) y [ROADMAP.md](ROADMAP.md) para el alcance y las decisiones del MVP.
