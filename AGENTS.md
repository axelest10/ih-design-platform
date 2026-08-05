# Instrucciones del repositorio

- Mantén separadas las fuentes autorizadas de datos comerciales y las salidas de IA.
- Nunca agregues secretos, claves API o credenciales a Git.
- Los logos y textos críticos deben componerse mediante plantillas controladas.
- Ejecuta `ruff check .`, `python manage.py check` y `pytest` antes de cada cambio estructural.
- Actualiza `TASKS.md` y `DECISIONS.md` cuando cambie el alcance o la arquitectura.
- Usa migraciones para los cambios de modelos y conserva trazabilidad de las versiones de diseño.
