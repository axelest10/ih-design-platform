# Instrucciones del repositorio

## Workflow de ramas y pull requests

- No trabajes directamente sobre `main`, salvo una corrección documental explícitamente autorizada.
- Crea una rama por entrega: `feature/<alcance>`, `fix/<alcance>` o `docs/<alcance>`.
- Mantén cada entrega independiente; no mezcles cambios de features distintos en una misma rama o PR.
- Parte siempre de `main` actualizado con `git pull --ff-only`.
- Antes de abrir un PR, ejecuta `ruff check backend tests`, `python manage.py check`, `python manage.py makemigrations --check --dry-run` y `pytest -q`.
- El PR debe apuntar a `main`, explicar el alcance, incluir las migraciones y pruebas relacionadas, y registrar los cambios de arquitectura en `DECISIONS.md`.
- No reescribas historia compartida ni hagas force-push salvo autorización explícita.
- Después de abrir el PR, deja la rama disponible para revisión; el merge a `main` lo hace el flujo de revisión del equipo.

- Mantén separadas las fuentes autorizadas de datos comerciales y las salidas de IA.
- Nunca agregues secretos, claves API o credenciales a Git.
- Los logos y textos críticos deben componerse mediante plantillas controladas.
- Ejecuta `ruff check .`, `python manage.py check` y `pytest` antes de cada cambio estructural.
- Actualiza `TASKS.md` y `DECISIONS.md` cuando cambie el alcance o la arquitectura.
- Usa migraciones para los cambios de modelos y conserva trazabilidad de las versiones de diseño.
