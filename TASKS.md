# Tareas

## Completadas

- [x] Elevar Pillow a `>=12.3,<13.0` para cerrar los hallazgos vigentes de `pip-audit`
      heredados de `main` antes de promover el hotfix de correo (2026-08-15).
- [x] Sustituir el adaptador runtime de Resend por Postmark, con remitente aprobado, Reply-To
      opcional, `MessageID` seguro y política `disabled|allowlist|live` que falla cerrada
      (2026-08-15).
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

- [ ] Instalar directamente en Railway el token del servidor **IH Design — Staging**, configurar
      la allowlist de prueba aprobada y ejecutar una verificación sin destinatarios reales.
- [ ] Promover mediante PR separado el hotfix provider-only a Production, comprobar correo con
      SSO apagado y después revocar la clave Resend expuesta en el workspace propietario.

- [x] **Ratificación de los productos default de la paquetería de colegios** (`qc-2026`,
      `teacher-training-certifications`) — Axel confirmó ambos productos el 2026-08-08. La
      decisión queda trazada junto a la lista de prioridad en
      `backend/materials/services/catalog.py` y en `DECISIONS.md`.
- [x] **Primer commit grande del trabajo acumulado** — realizado el 2026-08-08 en commits
      lógicos, después de limpiar los archivos temporales sueltos de la raíz.
- [ ] **Crear el entorno de staging real** (PostgreSQL + auth corporativa + almacenamiento
      persistente) siguiendo `docs/operations/deployment.md` — la documentación y variables ya
      están listas, falta aprovisionar el proveedor (Railway o Render).
- [ ] Recibir catálogo comercial autorizado de los productos piloto.
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
