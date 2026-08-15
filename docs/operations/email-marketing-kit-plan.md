# Diseño: `email-marketing-kit`

## Alcance de esta fase

`email-marketing-kit` generará una vista previa HTML y un archivo HTML descargable para revisión
y exportación manual. No enviará correos, no conectará un proveedor SMTP/API, no gestionará listas
de suscriptores y no tocará `backend/security/`. El envío real requiere una decisión y credenciales
operativas aparte.

## Datos necesarios

El paquete reutilizará `MaterialBundle`, `Campaign` y el catálogo activo. Su `brief_context` deberá
aportar únicamente el contexto editorial y de marca que el email no puede inferir:

- `brand_logo_key` y, opcionalmente, `additional_logo_keys` aprobados.
- `subject`, `preheader`, `headline`, `body`, `cta_label` y `cta_url`.
- `audience`, `objective`, `language` y `unsubscribe_url` para la exportación.
- `copy_by_product` si el mismo paquete contiene una versión por producto.

La campaña seguirá siendo la fuente de verdad para copy comercial, beneficio, precio, CTA y
vigencia. Si el email promociona una campaña, se exigirá el mismo contrato de confirmación del
flujo sales-kit: campaña activa y vigente, copy aprobado, `source_status=confirmed`, `source_url`,
beneficio y CTA. Precios, descuentos, fechas o URLs no se inventarán.

## Formato y renderer

El entregable inicial será un email HTML de ancho máximo 600–640 px, con tablas para estructura,
CSS inline, tipografías seguras y degradación razonable en clientes de correo. No usará JavaScript,
iframes, video embebido, fuentes externas ni dependencias remotas para renderizar. Las imágenes
de marca se referenciarán como activos aprobados y el export deberá incluir los datos necesarios
para que el equipo decida cómo alojarlas.

El renderer será una familia nueva `email-html`, porque un HTML de página o social no garantiza
compatibilidad con clientes de correo. Aun así, reutilizará el pipeline existente:

`MaterialBundle → DesignBrief → Design → DesignVersion → revisión automática`.

El resultado se guardará como archivo `.html` mediante `default_storage`, igual que los PDF/PPTX
existentes, y la versión conservará `html_path`, el snapshot de campaña y un resumen de validación.

## Qué se reutiliza y qué es distinto

| Se reutiliza | Específico de email |
| --- | --- |
| catálogo activo y `Campaign` autorizada | contrato de asunto/preheader y enlace de CTA |
| logos y validación de acceso existentes | CSS inline, tablas y ancho máximo 640 px |
| `MaterialBundle`, briefs, diseños, versiones y revisión | validaciones de ausencia de JS, iframe, video y fuentes externas |
| almacenamiento configurado y endpoint de descarga | unsubscribe URL obligatoria para exportación |
| patrón de templates versionados | preview HTML independiente de `html-svg` |

## Entregable inicial

Se implementará un tipo `email-kit` con una plantilla base versionada y un entregable por bundle.
El flujo no enviará el email ni lo marcará como entregado: lo dejará en revisión con preview y
archivo HTML. La falta de datos editoriales obligatorios o de una campaña confirmada bloqueará la
generación con 400 y no creará piezas parciales.

No quedan preguntas de producto abiertas para esta implementación acotada: la decisión operativa
es exportar/visualizar únicamente. Si más adelante se solicita envío real, deberá definirse en un
PR separado el proveedor, consentimiento, listas, tracking, rebotes, unsubscribe y secretos.
