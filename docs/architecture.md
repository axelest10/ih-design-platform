# Arquitectura

```text
Cliente futuro
     |
     v
Django REST API ---- briefs ---- catálogo/campañas/sedes
     |                    |
     |                    v
     +---- diseños/versiones ---- validaciones ---- activos oficiales
     |
     +---- AIProvider ---- OpenAI (inicial)
     |
 PostgreSQL + pgvector (preparado) / Redis + Celery / S3
```

El backend organiza el dominio en aplicaciones Django independientes. Los briefs apuntan a entidades autorizadas y los diseños conservan versiones inmutables por número. El renderizado aún no está implementado: el campo `render_data` es el contrato de entrada para la futura capa HTML/SVG.

## Persistencia y procesos

- PostgreSQL es la base recomendada; las migraciones evitan acoplar el dominio a SQLite.
- `backend/config/celery.py` registra Celery con Redis como broker futuro.
- S3 se activa si existe `AWS_STORAGE_BUCKET_NAME`; el modelo de activos conserva checksum y reglas de uso.
- pgvector queda preparado a nivel de infraestructura/documentación, sin imponer todavía embeddings ni costos operativos.

## Seguridad de contenido

La información comercial autorizada es la fuente de verdad. El adaptador IA recibe `authorized_context` y aplica instrucciones de seguridad, pero las validaciones de campos críticos y la composición final deben ejecutarse en una plantilla controlada.
