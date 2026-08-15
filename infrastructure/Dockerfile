FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 120 --access-logfile - --access-logformat '%(h)s %(l)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\"' --error-logfile - --capture-output"]
