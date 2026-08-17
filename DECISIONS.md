# Decisiones técnicas

## 2026-08-16 — Revisión humana por versión

El endpoint `POST /api/v1/designs/{id}/review/` acepta `approve`, `reject` y `request_changes`
con una `DesignVersion` explícita. La versión guarda `review_status` (`pending`, `approved`,
`rejected` o `changes_requested`) y el diseño mantiene su estado agregado (`approved`, `rejected`
o `revision_requested`). Los rechazos y solicitudes de cambios requieren comentario, que se
persiste con `DesignReviewComment`; aprobar permite comentario opcional.

La transición vive en `backend/designs/services/review.py` para que futuras vistas o paneles no
dupliquen reglas. `notify_review_transition()` es un hook no-op: se reserva la integración de
notificaciones para una fase posterior, sin enviar mensajes ahora. No se toca `backend/security/`.

## 2026-08-16 — Historial y exportación WhatsApp sin envío

La revisión expone `GET /api/v1/designs/{id}/history/` con una línea de tiempo por `DesignVersion`,
incluyendo estado de revisión automática, validación y safe-zone. La interfaz conserva la selección
de versiones y muestra esos estados en el historial visible.

`output=whatsapp` reutiliza el renderer existente: para piezas sociales entrega el SVG con sus
dimensiones nativas (1080 × 1080, 1080 × 1350 o 1080 × 1920) como imagen descargable; para una
versión documental entrega el PDF persistido como documento. No se añade un renderer nuevo ni se
integra la API de WhatsApp.

## 2026-08-16 — Copy IA acotado a fuentes confirmadas

`POST /api/v1/material-bundles/{id}/suggest-copy/` está disponible para `venue-kit`, `sales-kit` y
`email-kit`. El contexto enviado al único proveedor actual (`OpenAIProvider`) se construye solo
desde productos/sedes/campañas con `source_status=confirmed`; venue-kit aplica además la
confirmación explícita de Axel para sus seis pilares. Un producto o campaña pendiente bloquea la
llamada.

La respuesta se guarda en `brief_context.ai_copy_draft` con `status=pending_approval`,
`needs_confirmation=true`, proveedor/modelo y contexto autorizado. Es un borrador para el flujo de
aprobación de la Fase 1: no crea ni modifica `DesignVersion` y no publica copy automáticamente.

## 2026-08-16 — Auditoría y calidad ligera para llamadas IA

`ai.AICallAudit` registra prompt/contexto autorizado, respuesta, proveedor, modelo, timestamp,
metadatos, estado y vínculo a `DesignBrief`, `DesignVersion` o `MaterialBundle` cuando existe. Se
registran también errores del proveedor para que la auditoría no pierda llamadas fallidas.

`validate_ai_output()` es una señal de calidad reutilizable, no una aprobación automática: marca
cifras y URLs ausentes del contexto autorizado y frases que parecen claims no verificables con
`needs_review`. No modifica el copy ni agrega un segundo proveedor; OpenAI continúa siendo el único
adaptador de generación y la revisión visual configurada conserva su proveedor actual.

## 2026-08-15 — Visibilidad y geometría del chequeo safe-zone

La revisión humana incorporará `validation_summary.safe_zone_check` en el mismo conjunto de
verificaciones que ya muestra `frontend/scripts/review.js`; se eligió adaptar la lectura del
frontend porque conserva el payload persistido y evita duplicar o reescribir checks en la señal.

No se mantiene una rama post-render `geometry-violation`: el renderer ya rechaza una región como
`logo_row` antes de crear `DesignVersion`, por lo que esa rama no sería alcanzable desde el flujo
normal. Safe-zone deja trazabilidad de esa garantía en `geometry.source=renderer.safe_area`, y el
caso de logo cerca del borde se prueba en el renderer, donde sí puede dispararse con una geometría
inválida. No se toca `backend/security/`.

## 2026-08-15 — safe-zone/legibilidad se persiste en `DesignVersion`

La comprobación se conecta al signal común de creación de `DesignVersion`, por lo que cubre las
versiones generadas por los flujos actuales y futuros que usen el modelo. Se guardan porcentajes,
límites, regiones, violaciones y contraste en `validation_summary.safe_zone_check`; no se añade un
modelo ni un estado paralelo.

La política inicial usa 6.67% lateral y los márgenes equivalentes a 72 px de los templates social
actuales: square 6.67% vertical, portrait 5.33% y story 3.75%. La legibilidad reutiliza la matriz
oficial documentada y exige 4.5:1 para texto normal. Un fallo conserva la versión para trazabilidad
y marca el resumen como `needs_changes`, pero no muta `claude_review_status` ni fuerza el estado
de `Design`; esos estados siguen perteneciendo a revisión automática/humana. Documentos, PPTX y
email reciben `skipped` porque no se inventa una zona social para ellos.
## 2026-08-15 — `email-kit` es export-only hasta definir el envío

La primera versión de `email-kit` genera un preview y un archivo HTML autocontenido para revisión
o exportación manual. Usa una familia de renderer distinta a HTML/SVG porque necesita tablas,
CSS inline, ancho máximo de 640 px, tipografías seguras y ausencia de JavaScript, iframes, video,
fuentes externas y otros embeds. Reutiliza el pipeline Brief → Design → DesignVersion, los logos
aprobados, `Campaign`, almacenamiento y revisión automática.

No se integra SMTP/API, proveedor de email, listas, tracking ni envío real. La generación exige
campaña activa/vigente con datos comerciales confirmados y `unsubscribe_url` en el contexto. Una
fase posterior deberá recibir luz verde para decidir proveedor, consentimiento, rebotes, tracking,
unsubscribe operativo y secretos. La implementación no toca `backend/security/`.
## 2026-08-15 — `sales-kit` depende de campañas comerciales autorizadas

La paquetería de ventas no crea un catálogo de precios ni una entidad paralela de ofertas.
Reutiliza `catalog.Product` para seleccionar el producto y `campaigns.Campaign` como fuente de
verdad para nombre, copy aprobado, vigencia y `offer_data`. La generación queda bloqueada si la
campaña está inactiva, fuera de vigencia, no tiene copy aprobado o no incluye `source_status`,
`source_url`, `benefit` y `cta` con estado confirmado.

El paquete genera piezas cuadrada, story, vertical, brochure A4 y presentación 16:9 reutilizando
los templates/renderers existentes. La campaña se copia como snapshot dentro de cada brief para
que una pieza no cambie retrospectivamente si se edita la campaña después. No se sembraron
precios, descuentos ni promociones reales: falta que Marketing entregue la primera `Campaign`
confirmada antes de usar el flujo fuera de pruebas. La implementación permanece separada de
`backend/security/`.
## 2026-08-15 — `venue-kit` usa seis pilares y datos oficiales por sede

- Axel confirmó que todas las sedes venden los seis pilares existentes: `general-english`,
  `cambridge-exam-preparation`, `university-programmes`, `business-english`,
  `ielts-preparation` y `spanish-courses`. Son las prioridades de `venue-kit`, pero la selección
  acepta futuros slugs activos del catálogo.
- El paquete cubre social, documento A4 y presentación mediante los renderers existentes; no se
  crea un renderer nuevo. El CTA y la decisión de usar mapa, QR, fotografía o logos adicionales
  pertenecen al brief/diseño, no a un default de sede.
- `Branch` guarda `country` y `source_url`; `official_contact_data` normaliza ubicación, contacto,
  `source_status` y `needs_confirmation`. La generación solo acepta sedes con fuente, dirección
  y teléfono confirmados. Horarios, mapa, CTA y assets locales quedan pendientes.
- Las sedes iniciales se cargan desde las páginas oficiales documentadas en
  `docs/operations/venue-marketing-kit-plan.md`; no se inventan datos fuera de esas fuentes.

## 2026-08-15 — Diseño inicial de `venue-kit` (superseded by confirmed implementation)

- Se propone reutilizar `MaterialBundle`, `MaterialBundleItem`, briefs hijos, templates y renderers existentes de `school-kit`.
- No se inventan programas, contactos, direcciones, mapas, horarios ni deliverables por defecto para una sede.
- Esta entrada queda reemplazada por la decisión inmediatamente anterior, después de las
  confirmaciones de Axel sobre los seis pilares, las fuentes oficiales y las tres familias de
  formato.

## 2026-08-15 — La verificación R2 se ejecuta en staging, no en local

Como este entorno no tiene bucket, endpoint ni credenciales R2 disponibles, no se simula una
verificación de red ni se agregan secretos al repositorio. Se añade el comando
`python manage.py verify_storage_backend`, que exige `storages.backends.s3.S3Storage`, un bucket y
un endpoint `*.r2.cloudflarestorage.com`; en ejecución normal guarda un objeto temporal, confirma
existencia y contenido leído, lo elimina y reporta `result=passed`. `--dry-run` solo valida la
configuración. La evidencia real queda pendiente de ejecutar en staging con credenciales fuera de
Git.

## 2026-08-15 — Generaciones pesadas pasan a Celery

Las generaciones de PDF, PPTX y copy que requieren proveedor de IA se ejecutan mediante tareas
Celery, no dentro del ciclo síncrono de una vista. Cada solicitud crea un `AsyncGenerationJob`
propio, devuelve `202 Accepted` con `task_id` y `status_url`, y el frontend consulta
`GET /api/v1/tasks/<task_id>/` hasta obtener `succeeded` o `failed`. El job guarda propietario,
recurso, resultado y error para no exponer resultados de otra persona. El modo eager sólo se usa
en tests; staging y producción requieren un worker real conectado a Redis.

## 2026-08-15 — Nuevas escrituras de archivos quedan aisladas por usuario

- Los uploads de logos, referencias de brief y activos de marketing usan rutas `users/{user_id}/...` mediante funciones `upload_to`.
- Los PDF/PPTX generados usan el propietario del brief en `users/{user_id}/generated-designs/{design_id}/...`.
- Registros sin propietario explícito se escriben bajo `users/unassigned/`; esto evita volver a crear claves planas.
- Los objetos existentes con claves históricas planas no se renombran automáticamente. La migración física queda como operación explícita posterior para no romper URLs, referencias o procesos activos.

## 2026-08-15 — IH Hub SSO queda definido como integración futura, no activa

- IH Hub entrega un `apiToken` JWT HS256 con `sub`, `tenantId`, `email` y `exp`; design-platform lo validará más adelante con el secreto compartido `IHLATAM_SSO_SECRET`.
- Se decide transportar el token inicialmente en el enlace de entrada (`?sso=`) y canjearlo una sola vez por `POST` sobre HTTPS; no se implementa endpoint, middleware ni vista en esta fase.
- El SSO será una vía adicional: token ausente, inválido o expirado devuelve al magic-link existente sin tocarlo ni reemplazarlo.
- `tenantId` se conservará en una identidad externa futura asociada al usuario local para seleccionar país/marca LATAM; no se confiará en valores enviados por el navegador.
- La implementación está bloqueada hasta recibir el secreto real, confirmar expiración/claims y coordinar con quien mantiene el Hub el enlace hacia design-platform. Requiere luz verde explícita de Axel.

## 2026-08-09 — Hello Live English: se revierte la decisión del 2026-08-05, se adopta identidad propia

Axel aportó el Brandfolder real del proveedor (`Brandfolder-Hello Live English.pdf`, Canva,
autora Alejandra Tello, creado el 2026-08-07), que no estaba disponible cuando se tomó la
decisión anterior basándose en un deck interno impreciso. Tras verificar visualmente cada página
del Brandfolder, Axel confirmó explícitamente “Adoptarla ahora” el 2026-08-09. Por tanto, se
revierte la parte de la decisión del 2026-08-05 que trataba Hello Live English como una identidad
sin paleta propia.

“Hello!” continúa siendo el nombre comercial del pilar institucional Inglés General y conserva
Youth Green cuando aparece en materiales institucionales de IH. La identidad independiente de la
marca **hello**, el producto **Live English** y su sub-variante **Live English Kids** se registra
por separado en `brand/product-colors/sub-brand-identities.yaml`; no se incorporó directamente a
`authorized-colors.yaml` para evitar confundir la paleta institucional de IH con la del sub-brand.

En la página de paleta también aparecen los códigos sueltos `#f4a261`, `#c4c4c4`, `#ef642e` y
`#000000`. Se descartaron porque no tienen nombre ni relación visual con ninguno de los ocho
swatches nombrados y corresponden a texto de plantilla de Canva sin editar.

## 2026-08-09 — Tamaño estándar y dual-branding operativo para redes sociales

Axel confirmó en chat dos extensiones operativas para `brand/documentation/logo-rules.md`. Ambas
tienen estado `mx_designated` y no provienen del manual oficial:

1. Para nuevas piezas con canvas de 1080px de alto se recomienda un isotipo de 80–90px de
   diámetro y un lockup completo de aproximadamente 2.3–2.7 veces ese diámetro. El estándar se
   deriva de una medición empírica sobre una muestra de 80 de los 316 diseños reales del catálogo,
   con 13 detecciones confiables; coexiste con el mínimo de legibilidad ya documentado y no lo
   reemplaza.
2. Para piezas de redes sociales con logos de colegio o socio se permiten hasta 4 logos en total,
   siempre con IH primero o con prioridad de posición. Los layouts dependen de si participan 2, 3
   o 4 logos; su tamaño se equilibra por peso visual mediante alineación óptica, y se usa una
   pleca sólida detrás del lockup cuando el fondo no asegure contraste.

Estas reglas son adicionales y distintas del caso oficial “IHWO Member” del manual global, que
permanece intacto.

## 2026-08-08 — Productos prioritarios del `school-kit` confirmados por Axel

Axel ratificó `qc-2026` y `teacher-training-certifications` como productos prioritarios por
defecto para la paquetería de colegios. La selección queda trazada también junto a la lista de
prioridad en `backend/materials/services/catalog.py`; el `school-kit` puede seguir reutilizando
los demás productos activos del catálogo.

## 2026-08-04 — Django modular como núcleo

Se elige Django + Django REST Framework para acelerar el MVP, mantener un modelo relacional explícito y exponer una API consumible por un frontend futuro.

## 2026-08-04 — Datos críticos fuera de la IA

Precios, fechas, promociones, logos, sedes, teléfonos y CTA se modelan como datos/activos autorizados y se reservan para la composición controlada. La IA recibe contexto permitido, pero no es fuente de verdad comercial.

## 2026-08-04 — SQLite local, PostgreSQL preparado

El entorno local y las pruebas usan SQLite por defecto para no requerir servicios externos. PostgreSQL se activa mediante `DB_ENGINE=postgresql` y es la configuración recomendada para staging/producción.

## 2026-08-04 — Interfaz de proveedor IA

`AIProvider` define el contrato interno. `OpenAIProvider` es el único adaptador inicial; la aplicación no importa directamente un SDK de otro proveedor.

## 2026-08-05 — `brand/` como sistema de marca basado en archivos, no solo en base de datos

Los tokens de marca (colores, tipografía, espaciado, colores por producto) viven como YAML en
`brand/tokens/` y `brand/product-colors/`, con un generador (`brand/scripts/generate_tokens.py`)
que produce JSON/CSS/JS/Tailwind sin duplicar valores a mano. El modelo `BrandGuideline`
existente en base de datos se sincroniza desde estos archivos vía
`python manage.py sync_brand_guideline`, en vez de ser la fuente primaria. Motivo: `brand/`
debe poder reutilizarse en proyectos que no comparten esta base de datos (otro frontend, otra
plataforma), y los archivos son más fáciles de versionar/revisar en pull requests que filas de
base de datos.

## 2026-08-05 — Fuente oficial de colores por producto: confirmada por el cliente

Existían tres documentos con mapeos de color por producto/pilar distintos entre sí
(`Color por producto.pdf`, `IH_Sistema_Colores_v2.docx`, `IH_Mexico_Sistema_Diseno_Web.docx`).
El cliente confirmó el 2026-08-05, con el documento adicional `IH_BRANDING_MARCA.docx`, que
`IH_Mexico_Sistema_Diseno_Web.docx` es la fuente correcta para los 6 pilares de negocio. Esa
decisión y las fuentes descartadas quedan documentadas en
`brand/product-colors/authorized-colors.yaml`.

## 2026-08-05 — Rainbow institucional: versión oficial del manual global, no la variante MX

El manual oficial (PDF) define el rainbow de 8 colores incluyendo Light Orange (#F4AB63). Un
docx de México documentaba una variante que sustituía ese color por un "Teal" (#407B98) no
presente en ninguna paleta oficial. El cliente confirmó el 2026-08-05 usar la versión del
manual oficial; la variante MX queda registrada como rechazada en
`brand/tokens/colors.yaml -> rainbow.rejected_variant`.

## 2026-08-05 — No se redistribuye la tipografía Aptos sin licencia confirmada

Open Sans se incluyó en `brand/assets/fonts/open-sans/` (licencia SIL OFL 1.1, verificada).
Aptos no se incluyó: es la tipografía por defecto de Microsoft Office y ningún documento fuente
especifica los términos de licencia para redistribuir sus archivos `.ttf` dentro de un
repositorio. Se deja como pregunta pendiente para el cliente en `brand/assets/fonts/README.md`
y `brand/tokens/typography.yaml` (`license_status: UNKNOWN`), con Arial como fallback CSS
documentado mientras tanto.

## 2026-08-05 — Ratio de contraste: sí existe en el manual, estaba renderizado como imagen

La página "Contrast and Accessible Colours" del manual global no se detectó inicialmente
porque su contenido numérico está renderizado como tabla/imagen, no como texto extraíble por
`pdftotext`. Al renderizar la página a 150dpi se confirmó una matriz oficial de contraste para
las 10 combinaciones de color institucionales (8 colores + blanco + negro), con niveles
AAA (≥7:1) / AA (≥4.5:1) / AA18 texto grande (≥3:1) / DNP (<3:1) — umbrales idénticos a WCAG
2.1. Se documentó la matriz completa en `brand/documentation/accessibility-rules.md` y se
actualizó `brand/tokens/colors.yaml -> contrast_and_accessibility` de `mx_extension` a
`approved`. La cifra "4.5:1" que ya usaba el checklist de México (`IH_Mexico_Sistema_Diseno_Web.docx`,
9.3) coincide exactamente con el umbral AA oficial, sin contradicción.

## 2026-08-05 — Aptos: no se redistribuye; licencia estándar de Microsoft no lo permite

Se investigó la licencia de Aptos (WebSearch, 2026-08-05). Microsoft publica una descarga
oficial y gratuita, pero la licencia estándar que la acompaña autoriza *usar* la fuente para
crear/mostrar/imprimir contenido, no *redistribuir* los archivos `.ttf` dentro de un
repositorio o dependencia interna reutilizable — eso requiere licenciamiento empresarial
separado gestionado directamente con Microsoft. Se actualizó `license_status` en
`brand/tokens/typography.yaml` de `UNKNOWN` a `RESTRICTED_STANDARD_LICENSE` y se documentó el
hallazgo en `brand/assets/fonts/README.md`. Los archivos `.ttf` de Aptos siguen sin incluirse;
queda pendiente que el cliente confirme si IH México ya cuenta con licenciamiento empresarial
de Microsoft para redistribución.

## 2026-08-05 — Tamaño mínimo de logo: designado por extensión MX, no es cifra oficial

Se confirmó visualmente (render 150dpi de la página "Logo Size") que el manual global no trae
ninguna cifra numérica de tamaño mínimo de reproducción. Por instrucción del proyecto, se
designó un mínimo derivado de reglas ya documentadas (zona de exclusión, regla de video al 30%
del ancho de pantalla, prohibición de distorsión/ilegibilidad): 24px/10mm para el isotipo solo,
32px/15mm para isotipo + wordmark, 48px/20mm para el lockup completo con texto secundario. Se
documentó en `brand/documentation/logo-rules.md` con `status: mx_designated`, explícitamente
pendiente de aprobación formal por el cliente/Marketing — no se presenta como cifra oficial del
manual.

## 2026-08-05 — "Live!"/"Hello!" y "UP": alias comerciales confirmados, sin paleta propia

El cliente confirmó que "Live!" (renombrado "Hello!") = pilar "Inglés General" y "UP" =
"University Programmes", ambos como simples alias comerciales del mismo pilar y color
institucional ya existentes (Youth Green y Knowledge Blue respectivamente) — no como pilares
nuevos. Se investigó Google Drive buscando un logo de "Hello" y no se encontró ninguno (la
subcarpeta "Hello Live" del enlace compartido está vacía; "Hello Live Pictures" solo contiene
fotos de staff). Se detectó además un deck interno ("Hello Live English — Presentación
Directores") que describe a "Hello Live English" con una identidad visual propia (paleta
Navy/Cian/Verde/Naranja/Magenta/Morado, logo de burbuja de chat, tipografía Poppins, dominio
helloliveenglish.com), distinta de la de IH. Se presentó este hallazgo al cliente, quien
decidió explícitamente NO adoptarla aquí: "Hello!" se documenta como alias simple, usando el
color y logo institucionales de siempre. Queda registrado en
`brand/product-colors/authorized-colors.yaml -> alias_note` para no perder el contexto si en el
futuro se decide adoptar la identidad independiente.

## 2026-08-06 — Tres preguntas del catálogo resueltas por el cliente

El cliente confirmó: (1) "IELTS LATAM" es solo la carpeta de marketing regional de
`ielts-preparation`, no un producto distinto — se movió `ielts-latam-regional-program` a
`deprecated` (`superseded_by: ielts-preparation`) y se re-etiquetaron sus 107+ referencias. (2)
"QC" = Quality Circle, programa para colegios (K-12) con convenio institucional con IH — se
actualizó `qc-2026` con esa identidad y `status: confirmed`. (3) Certificaciones docentes
(CELTA/DELTA/TKT/CAM/DIEELE) se venden en cada país usando el logo institucional de ese país,
sin logo propio — se confirmaron los 4 países y `status: confirmed` en
`teacher-training-certifications`, dejando `associated_logo_keys` vacío a propósito (no un logo
fijo). También indicó que la pieza mexico/6-nov4 (webinar de IA, color Technology Purple)
"seguramente" es de QC — se reasignó con `needs_review: true` porque "seguramente" no es
confirmación cerrada.

## 2026-08-06 — Catálogo de productos y anotación visual: capas separadas, no se toca lo generado

`brand/knowledge/product-catalog.yaml` se creó como fuente nueva (no existía catálogo previo en
`products/` ni en `backend/catalog/`, ambos vacíos). Para las 454 referencias visuales, en vez
de editar a mano `artwork-reference-knowledge.json` (generado), se creó una capa de anotaciones
separada y versionable (`brand/knowledge/artwork-annotations.yaml`: default + heurísticas +
overrides por id) que `brand/scripts/build_design_knowledge.py` fusiona con
`brand/assets/artwork-references/manifest.yaml` al regenerar. Solo 15/454 assets (muestra de
calibración, 3 por país + 3 de IELTS LATAM) tienen revisión visual humana real; el resto queda
con `annotation_status: metadata-only` y `needs_review: true` — no se inventó contenido visual
para el resto por no ser verificable sin revisión humana o de imagen adicional. Se descubrió por
inspección visual directa (no por documento de marca) una línea de producto no catalogada:
certificaciones docentes (CELTA/DELTA/TKT/CAM/DIEELE) — se agregó como
`teacher-training-certifications` con `status: inferred`, sin pilar ni color asignado.

## 2026-08-06 — Segunda pasada de revisión visual humana: 15 → 40/454, hallazgo de TEA

Con el "ok" del cliente para ampliar la muestra, se revisaron 25 imágenes adicionales (5 por
país + 5 de IELTS LATAM, muestreo aleatorio excluyendo las 15 ya revisadas) y se agregaron como
`overrides:` en `artwork-annotations.yaml`. Total acumulado: 40/454 con revisión visual humana
real. Hallazgos relevantes: (1) un partner/certificación no catalogado, **TEA — Test of English
for Aviation**, visto dos veces en Colombia (`21-feb2`, `16-ene1`) — se agregó a
`product-catalog.yaml` como `tea-test-of-english-for-aviation` (`brand_scope: partner`,
`status: inferred`, solo Colombia por ahora, sin logo propio cargado); (2) confirmación adicional
de que `teacher-training-certifications` se vende también en México (imagen "Certifícate en:
DIEELE, CELTA, DELTA, CAM, TKT") y en variante de español (DIEELE) en México y Colombia; (3) la
plantilla de la pieza mexico/6-nov4 (QC, `needs_review: true`) se encontró duplicada en Colombia
— se etiquetó igual, con la misma reserva ("seguramente" no es confirmación cerrada); (4) una
pieza de Perú ("certifícate como docente de idiomas con University Programmes!") genera
ambigüedad genuina entre `university-programmes` y `teacher-training-certifications` — se dejó
`needs_review: true` con nota explicativa en vez de forzar una sola atribución; (5) una campaña
de "cursos en línea" en México (mexico/12-ene3) no permitió determinar pilar/producto con
certeza — se dejó `product_slug: null`. No se inventó ningún dato: donde la imagen no daba
certeza, se mantuvo `needs_review: true` con `review_note` explicando la ambigüedad exacta.

## 2026-08-07 — Visión ampliada a plataforma LATAM multi-material, en paralelo al MVP

Axel confirmó que la ambición real de la plataforma es mucho mayor a la descrita en
`PROJECT.md`/`ROADMAP.md`: no solo piezas sociales de México, sino una plataforma a nivel LATAM
para todo tipo de material de marketing (mailings/correo, paquetería de colegios, paquetería de
sedes, paquetería de ventas). Confirmó además, ante la disyuntiva explícita entre "visión norte
con MVP angosto" (recomendado, siguiendo el propio principio de alcance angosto del documento
modelo IH Connect) y "empezar ya en paralelo", elegir la segunda opción — construir la expansión
en paralelo al MVP actual, no después de validarlo. Orden de prioridad confirmado: colegios →
sedes → ventas → mailings. Documentado en `IH_Design_Platform_Scoping_Document_v2.docx` en
adelante (Sección 2.1) y registrado como riesgo aceptado conscientemente (Sección 31.6), no como
recomendación de Claude.

## 2026-08-07 — Documento de scoping adaptado del formato IH Connect v2, con conciliación Codex

Axel compartió el documento de scoping "IH Connect v2" (IHWO, proyecto de plataforma de eventos
para escuelas) como modelo de estructura y rigor a seguir para futuros documentos de planeación.
Se adaptó al estado real de `ih-design-platform` (no se copiaron secciones que no aplican, como
safeguarding de menores o SSO institucional) en
`IH_Design_Platform_Scoping_Document_v1.docx`. Se envió un prompt de status-check a Codex; su
respuesta (verificada directamente contra el repo, no tomada literalmente) se fusionó en v3,
corrigiendo: conteo real de pruebas (89→95→103), alcance real de dual-branding (ya implementado,
a diferencia de lo que decía v2) vs. white-reversed (sigue pendiente), estado real de verificación
de zona segura/legibilidad (no implementada), alcance real de `admin.html`, y conteos reales del
lote de 50 piezas de prueba (0/50, no arrancado). Codex generó su propia versión corregida
(`IH_Design_Platform_Scoping_Document_v1_consolidated.docx`, sobre v1, sin la visión LATAM) — se
usó como insumo para la fusión, no como reemplazo del documento de Claude.

## 2026-08-07 — Primer paso de ejecución del plan por Codex: PASO 0-2, PASO 5, PASO 6 (diseño) y PASO 8 (parcial)

Se envió a Codex un plan de ejecución paso a paso (v3 del documento de scoping) con orden de
prioridad explícito. Codex ejecutó, sin reportarlo explícitamente salvo el último (se descubrió
revisando el repo, no por su reporte): PASO 0 (corrección de `PROJECT.md` sobre el rol de Claude),
PASO 2 (CI ahora valida `brand/generate_tokens.py --check`, `generate_product_catalog.py --check`
y la reproducibilidad de `artwork-reference-knowledge.json`), PASO 5 (templates `story-v1` y
`portrait-v1`, registrados en `frontend/templates/manifest.yaml`), documentación de PASO 1
(`docs/operations/deployment.md`, sin desplegar) y PASO 6 (recomendación de diseño en
`docs/operations/approval-flow.md`, sin implementar). Reportó explícitamente el PASO 8 (parcial):
módulo `backend/materials/` con tipo de material `school-kit`, template `school-kit-v1`, y
reutilización del catálogo de productos para la paquetería de colegios — pero fijó `qc-2026` y
`teacher-training-certifications` como productos default sin la confirmación explícita de Axel
que el plan pedía antes de empezar ese paso. Verificado por Claude directamente (no solo por el
reporte de Codex): 103 pruebas, ruff y `manage.py check` en verde. Se detectó además que hay 95
archivos sin commitear desde el commit inicial del repo, y archivos temporales sueltos en la raíz
(`_tmp_v3/`, `_tmp_v3.zip`, etc.) que deben limpiarse. Todo documentado en
`IH_Design_Platform_Scoping_Document_v4.docx` Sección 31.7.

## 2026-08-05 — Logos: carga parcial desde carpeta local del cliente, no desde Google Drive

El cliente compartió un enlace a una carpeta de Google Drive
(`https://drive.google.com/drive/folders/14TZxcHMkSnnwWfwSk6fmxI2Ck1aZ9FeM`) para cargar los
logos oficiales. La subcarpeta "Ih México" de ese Drive solo contenía dos exportaciones casi
idénticas del logo a color, sin variantes negro/blanco ni vectorial. Se usó en su lugar una
carpeta que el cliente ya tenía en su máquina ("Logotipos IH MX Y QC"), con el mismo diseño en
4 archivos (color PNG, negro PNG, blanco PNG y vectorial AI) — un conjunto más completo. Se
cargaron y aprobaron las variantes `classic`, `black` y `white` en
`brand/assets/logos/manifest.yaml`; `white-reversed` y `dual-branding` siguen pendientes por no
encontrarse en ninguna de las dos fuentes. Otras subcarpetas de ese Drive (p. ej. "Cambridge")
contienen activos de un dominio distinto (insignias de certificación Cambridge English
Qualifications) y no deben confundirse con el logotipo institucional de IH México.
