# Tareas

## Estabilización y certificación (2026-08-22)

- [x] Exponer en el healthcheck el SHA/rama/entorno/servicio reales inyectados por Railway, sin
      consultar infraestructura ni hardcodear una versión.
- [ ] Alinear staging y producción con `main` y documentar el SHA efectivo de ambos entornos.
- [ ] Certificar en staging el flujo real brief square → generación → persistencia → revisión →
      aprobación → descargas → entrega.
- [ ] Verificar desde Railway PostgreSQL persistente, escritura R2, Redis, worker Celery y una
      tarea asíncrona real con `CELERY_TASK_ALWAYS_EAGER=0`.

- [x] **Flujo de revisión y aprobación** — `DesignVersion` persiste estados pendientes,
      aprobados, rechazados o con cambios solicitados; `POST /api/v1/designs/{id}/review/`
      persiste comentarios y deja un hook preparado para notificaciones futuras.

- [x] **Historial visible y exportación WhatsApp** — el endpoint `history` expone la línea de
      tiempo por versión y `output=whatsapp` entrega el SVG social o PDF documental listo para
      compartir; no integra la API de WhatsApp.

- [x] **Sugerencias de copy IA para venue/sales/email** — usa únicamente catálogos, sedes y
      campañas con datos confirmados; guarda el resultado como `pending_approval` y no lo aplica
      directamente a ningún diseño.

- [x] **Trazabilidad y calidad de IA** — cada llamada registra prompt, respuesta, proveedor,
      modelo, timestamp y vínculo al brief/DesignVersion/material disponible; las respuestas
      reciben una validación ligera de cifras, URLs y claims no verificables.

## Venue-kit (2026-08-15)

- [x] Axel confirmó que todas las sedes comparten los seis pilares del catálogo:
      `general-english`, `cambridge-exam-preparation`, `university-programmes`,
      `business-english`, `ielts-preparation` y `spanish-courses`.
- [x] Reconciliar `spanish-courses` en el catálogo con esa confirmación: aplica a las sedes activas
      de MX, CO, PE y CL, sin quedar pendiente de confirmación.
- [x] Implementar `venue-kit` con piezas sociales, documento A4 y presentación, reutilizando
      los renderers existentes y dejando abierto el catálogo para futuros slugs activos.
- [x] Cargar sedes iniciales de México, Colombia, Perú y Chile con fuente oficial, dirección y
      contacto; conservar pendientes de horario, mapa, CTA y assets locales.
- [x] Revisar y fusionar el PR de `venue-kit` contra `main`.

## Completadas

- [x] Mover las generaciones de PDF, PPTX y copy de IA a Celery (`feature/celery-worker-railway`):
      las vistas devuelven `202` con `task_id`/`status_url`, y el estado queda persistido en
      `AsyncGenerationJob`. Railway requiere un segundo servicio con
      `celery -A config worker -l info --concurrency=2`.
- [x] Implementar storage user-scoped para uploads y archivos generados en `feature/user-scoped-storage`; las claves históricas quedan documentadas sin migración automática.
- [x] Documentar el plan de integración SSO con IH Hub en `docs/operations/ihlatam-sso-plan.md`; la implementación queda bloqueada hasta recibir el secreto real y la autorización explícita de Axel.
- [x] Documentar el workflow de ramas y pull requests en `AGENTS.md` mediante `docs/branching-workflow`.

- [x] Crear base modular Django y DRF.
- [x] Separar branding, catálogo, campañas, briefs, diseños, activos, validaciones e IA.
- [x] Añadir contrato JSON Schema para briefs.
- [x] Preparar PostgreSQL, Redis, Celery y almacenamiento S3.
- [x] Añadir health endpoint, pruebas y GitHub Actions.
- [x] Construir `brand/` como sistema de marca reutilizable (tokens, colores por producto,
      activos, documentación) a partir de los manuales oficiales de IH México (2026-08-05).
- [x] Integrar `backend/branding/services/` (loader + validadores) y endpoints
      `/api/v1/branding/tokens/` y `/api/v1/branding/validate-color/`.
- [x] Extraer y organizar iconografía, rainbows y globos oficiales en `brand/assets/`.
- [x] Preparar `brand/assets/logos/` (estructura, manifest, validación) para la carga de logos.
- [x] Escribir pruebas de tokens, colores por producto, activos y consumo desde el backend
      (`tests/test_branding_tokens.py`, `tests/test_branding_assets.py`, `tests/test_branding_api.py`).
- [x] Cargar logotipos oficiales — variantes classic, black y white (2026-08-05), a partir de
      la carpeta local del cliente "Logotipos IH MX Y QC" y confirmadas contra la carpeta de
      Google Drive compartida. Registradas y aprobadas en `brand/assets/logos/manifest.yaml`.
- [x] Ampliar el catálogo a LATAM con logos regionales, globales, sub-marcas y partners;
      organizar por alcance/país y registrar 78 entradas en `brand/assets/logos/manifest.yaml`.
- [x] Exponer el catálogo aprobado mediante `GET /api/v1/branding/logos/`, con filtros por
      `scope`, `country`, `brand` y `variant`.
- [x] Crear el template versionado `square-v1` en HTML/SVG, renderizador determinista, preview
      con creación de `DesignVersion` y transición a `in_review`.
- [x] Agregar decisión de revisión `approve|reject` para cerrar el primer flujo de revisión.
- [x] Ratio de contraste oficial — encontrado (2026-08-05): matriz completa en la página
      "Contrast and Accessible Colours" del manual, documentada en
      `brand/documentation/accessibility-rules.md`.
- [x] Licencia de Aptos — investigada (2026-08-05): descarga oficial de Microsoft existe, pero
      la licencia estándar no permite redistribuir los `.ttf`; requiere licenciamiento
      empresarial. No se agregan los archivos sin confirmación del cliente.
- [x] Tamaño mínimo de logo — confirmado que el manual no trae cifra oficial; se designó un
      mínimo MX (24px/32px/48px según variante de lockup) marcado como `mx_designated`,
      pendiente de aprobación formal.

- [x] Catálogo de productos por país (`brand/knowledge/product-catalog.yaml/.json`, 15
      productos) y etiquetado de las 454 referencias visuales (`brand/knowledge/
      artwork-annotations.yaml` + `artwork-annotation-schema.json`), con filtros nuevos en
      `/api/v1/artwork-references/knowledge/` (2026-08-06). Ver brand/knowledge/README.md.
- [x] Aplicadas las 3 respuestas del cliente al catálogo (IELTS LATAM deprecado, QC = Quality
      Circle, teacher-training-certifications confirmado en 4 países) y ampliada la muestra de
      revisión visual humana de 15 a 40/454 (2026-08-06), con hallazgo de un partner nuevo (TEA —
      Test of English for Aviation) agregado al catálogo.
- [x] Documento de scoping/arquitectura/plan de desarrollo adaptado del formato "IH Connect v2"
      (2026-08-07), ahora en v4: `IH_Design_Platform_Scoping_Document_v4.docx`. Incorpora la
      visión ampliada de Axel (plataforma LATAM, todo tipo de material de marketing, construida
      en paralelo al MVP) y el primer reporte de avance de Codex, verificado directamente contra
      el repo. v1-v3 se conservan en el repo para historial.
- [x] Ejecución del plan paso a paso por Codex (2026-08-07): PROJECT.md corregido (rol real de
      Claude), CI valida `brand/`/`brand/knowledge/` (`.github/workflows/ci.yml`), templates
      `story-v1` y `portrait-v1` implementados, documentación de despliegue lista
      (`docs/operations/deployment.md`) sin desplegar todavía, recomendación de diseño para el
      endpoint legacy de aprobación (`docs/operations/approval-flow.md`), y primera base backend
      de la paquetería de colegios (`backend/materials/`, template `school-kit-v1`). Verificado:
      103 pruebas, ruff y `manage.py check` en verde.

## Siguientes

- [x] Confirmar los datos oficiales, la oferta local y el paquete inicial de `venue-kit` según
      `docs/operations/venue-marketing-kit-plan.md`; Axel confirmó los seis pilares y el PR de
      implementación ya está fusionado.

- [x] **Ratificación de los productos default de la paquetería de colegios** (`qc-2026`,
      `teacher-training-certifications`) — Axel confirmó ambos productos el 2026-08-08. La
      decisión queda trazada junto a la lista de prioridad en
      `backend/materials/services/catalog.py` y en `DECISIONS.md`.
- [x] **Safe-zone y legibilidad por `DesignVersion`** — cada versión registra un resultado
      determinista en `validation_summary.safe_zone_check`, con política porcentual por formato
      social y contraste AA 4.5:1 basado en `brand/documentation/accessibility-rules.md`.
- [x] **Diseño e implementación de `email-kit`** — exporta/visualiza HTML compatible con
      clientes de correo mediante tablas, CSS inline y un ancho máximo de 640 px. No envía
      mensajes ni integra proveedores; requiere Campaign confirmada y URL de baja.
- [x] **Diseño e implementación de `sales-kit`** — la paquetería reutiliza los productos
      activos y los renderers social, A4 y presentación existentes. Cada generación exige una
      `Campaign` activa, vigente, con copy aprobado y `offer_data.source_status=confirmed`;
      no se sembró ninguna oferta comercial real.
- [x] **Comando de verificación R2** — añadido `python manage.py verify_storage_backend` para
      staging; comprueba escritura, lectura y borrado contra Cloudflare R2 sin persistir secretos.
- [x] **Primer commit grande del trabajo acumulado** — realizado el 2026-08-08 en commits
      lógicos, después de limpiar los archivos temporales sueltos de la raíz.
- [x] **Verificar la disponibilidad pública del web de staging** — `https://mydesign.ihlatam.com`
      responde el healthcheck y sirve el frontend; la URL cruda de Railway queda como fallback
      técnico.
- [ ] **Completar el entorno de staging real** (PostgreSQL + auth corporativa + almacenamiento
      persistente) siguiendo `docs/operations/deployment.md` — el web público está confirmado,
      pero el aprovisionamiento y las variables de infraestructura no se pueden cerrar sin acceso
      al dashboard o shell de Railway.
- [ ] Recibir catálogo comercial autorizado de los productos piloto.
- [ ] **Confirmar overlays específicos por plataforma social** para sustituir o complementar la
      reserva base de los templates cuando Marketing entregue dimensiones oficiales.
- [ ] **Definir el envío real de emails en una fase aparte** — falta decidir proveedor, listas y
      consentimiento, tracking, rebotes, unsubscribe operativo y gestión de secretos. El flujo
      actual es export-only y no debe usarse como sender.
- [ ] **Recibir la primera `Campaign` comercial confirmada** (fuente, beneficio, CTA y vigencia)
      antes de usar `sales-kit` con datos reales; los tests usan datos sintéticos marcados como
      `source_status=confirmed`.
- [ ] **Ejecutar verificación R2 en staging real** — falta disponer del bucket, endpoint y
      credenciales del entorno de staging; local no se considera evidencia de escritura R2.
- [ ] **Confirmar el worker de Celery en staging** — falta acceso al dashboard o shell de Railway
      para verificar que existe el segundo servicio con `celery -A config worker -l info
      --concurrency=2`, que `CELERY_TASK_ALWAYS_EAGER=0` y que procesa una tarea real de PDF/PPTX.
- [ ] **Cargar las variantes de logo faltantes** (white-reversed, dual-branding) y, si es
      posible, versiones SVG de las variantes ya cargadas — ver
      `brand/assets/logos/README.md` → "Qué falta".
- [ ] **Confirmar si IH México tiene licenciamiento empresarial de Microsoft** para redistribuir
      los `.ttf` de Aptos; si sí, agregar los archivos y actualizar `license_status`.
- [ ] **Aprobar formalmente (o corregir) el tamaño mínimo de logo designado por MX** en
      `brand/documentation/logo-rules.md` (actualmente `mx_designated`, no `approved`).
- [x] **"Live!"/"Hello!" y "UP"**: confirmado por el cliente (2026-08-05) como alias
      comerciales de los pilares "Inglés General" y "University Programmes" — documentado en
      `brand/product-colors/authorized-colors.yaml` (`commercial_alias`). Se decidió
      explícitamente NO adoptar la identidad visual independiente vista en el deck "Hello Live
      English — Presentación Directores" (paleta/logo/tipografía propios); "Hello!" usa el
      color institucional Youth Green como siempre.
- [ ] **Logo de "Hello!"**: no se encontró ningún archivo en Drive (la subcarpeta "Hello Live"
      está vacía; "Hello Live Pictures" solo tiene fotos de staff). Como "Hello!" es alias del
      pilar Inglés General, usa el logo institucional de IH México ya cargado — no aplica
      cargar un logo distinto salvo que el cliente decida adoptar la identidad visual propia
      del deck más adelante.
- [ ] Definir roles, permisos y proveedor de identidad corporativa.
- [ ] Diseñar y versionar las primeras plantillas HTML/SVG (consumiendo `brand/generated/` y
      `brand/assets/`).
- [ ] Acordar checklist de aprobación con Marketing.
- [ ] Validar y aprobar formalmente los tokens de `brand/tokens/motion.yaml` (actualmente
      marcados como no oficiales/provisionales).
