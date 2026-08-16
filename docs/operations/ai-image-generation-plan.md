# Plan de generación de imágenes con IA

**Estado:** diseño para revisión. No implementado. No cambia el renderer actual ni activa generación de imágenes.

**Objetivo:** definir una capacidad futura que genere una imagen visual con IA a partir de un brief, manteniendo el control de marca de International House y conservando el flujo actual de plantillas como ruta segura.

## 1. Decisión recomendada

La primera implementación debe ser un modo adicional, detrás de una bandera de feature flag y con `template` como valor predeterminado:

```text
generation_mode = template | ai_image
```

`ai_image` no debe reemplazar el renderer actual. Debe producir una imagen base y reutilizar el modelo de `DesignVersion`, las validaciones, la revisión humana y la entrega existentes. El texto final —copy, CTA y datos de contacto— debe componerse después de la generación con el renderer controlado por el proyecto, no dibujarse dentro de la imagen del modelo.

Esto reduce tres riesgos: que una salida experimental rompa las piezas actuales, que el modelo invente texto comercial y que el control tipográfico dependa de una imagen generada. La primera prueba debería limitarse a un formato social ya soportado (`square`, `story` o `portrait`) y a una campaña/pilar que Axel seleccione.

## 2. Modelo y proveedor candidato

### Recomendación inicial

Usar el proveedor OpenAI que ya existe para texto, pero mediante un adaptador separado de `OpenAIProvider` para imágenes. El candidato principal será el modelo de imágenes más reciente habilitado para la cuenta de producción en el momento de implementar —la documentación pública actual presenta GPT Image 2—. Para un piloto controlado se deben comparar también:

| Candidato | Uso propuesto | Decisión pendiente |
| --- | --- | --- |
| GPT Image 2 | Calidad y dirección creativa como candidato principal | Confirmar disponibilidad, precio y límites de la cuenta |
| `gpt-image-1` | Fallback de compatibilidad si GPT Image 2 no está disponible | Confirmar calidad mínima y costo |
| `gpt-image-1-mini` | Experimentos de costo/volumen, no default de marca | Confirmar si la calidad cumple el estándar visual |

La documentación oficial de OpenAI identifica GPT Image 2 en su overview y documenta `gpt-image-1`/`gpt-image-1-mini` en la página de modelos. DALL·E no se propone como nueva integración porque esa misma documentación lo marca como deprecated. La compatibilidad de retención de datos debe verificarse para el proyecto concreto antes de enviar briefs o imágenes de referencia; la documentación de controles de datos incluye GPT Image 1 y GPT Image 1 mini entre los modelos compatibles con zero data retention, sujeto a las condiciones del endpoint y de la cuenta.

Fuentes oficiales a verificar al implementar:

- [OpenAI Platform overview](https://platform.openai.com/overview?height=3448)
- [OpenAI Models](https://platform.openai.com/docs/models/o1%20.docx)
- [OpenAI data controls by endpoint](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)

La selección definitiva no debe codificarse en este documento como una promesa. Se guardará en configuración (`AI_IMAGE_MODEL`) cuando Axel apruebe el modelo, el costo por imagen, la resolución y el presupuesto mensual.

### Forma de integración futura

1. Validar el brief y reunir únicamente datos confirmados.
2. Construir un `VisualGenerationRequest` estructurado, separado del copy.
3. Llamar al adaptador de imágenes con el modelo configurado.
4. Guardar la imagen original como artefacto de la versión, con modelo, parámetros, hash y trazabilidad de la llamada.
5. Ejecutar validaciones automáticas de marca y legibilidad.
6. Componer encima el copy aprobado por el sistema, logo y CTA mediante el renderer actual.
7. Crear la `DesignVersion` en estado pendiente de revisión; nunca autoaprobar.

Los fallos del modelo, límites de costo o validaciones fallidas deben dejar la versión en un estado explícito de error/revisión, con mensaje accionable. No deben activar un fallback silencioso que cambie el modo solicitado sin dejar registro.

## 3. Del brief actual a un prompt visual

El campo `DesignBrief.generated_prompt` actualmente contiene **copy publicitario en texto plano** generado para edición y composición. No es un prompt visual para un modelo de imágenes y no debe reutilizarse con ese significado.

El futuro pipeline debe leer el brief estructurado y producir dos salidas distintas:

- `visual_prompt`: dirección de imagen, sin afirmaciones comerciales inventadas.
- `copy_context`: datos que el generador de copy/renderer usará para la capa de texto.

### Datos de entrada

El mapeo debe cubrir los campos actuales del brief y su `brief_data`:

| Dato del brief | Uso visual | Regla de seguridad |
| --- | --- | --- |
| `audience` / `audience_need` | Personas, contexto y nivel de formalidad visual | No inferir edad, profesión o identidad no indicada |
| `objective` / `campaign_info` | Intención narrativa y acción visual | No convertir objetivo en una promesa de resultado |
| `tone` | Dirección de arte: energético, académico, profesional, cultural, etc. | Solo valores del brief; si falta, usar dirección neutra |
| `visual_elements` | Objetos, composición, escenario y tratamiento fotográfico | No añadir productos, sedes o símbolos no autorizados |
| `required_information` | Lista de información que deberá aparecer en la capa de copy | Nunca pedir al modelo que la renderice como texto final |
| `cta` / `cta_destination` | Reserva de espacio y jerarquía para el CTA posterior | No inventar URL, teléfono, precio o disponibilidad |
| `product_slug` | Pilar, color y restricciones de producto | Debe existir en catálogo y estar confirmado |
| `country` / sede | Contexto local si la fuente está confirmada | No inventar monumentos, dirección o atributos de sede |
| `channel` / formato | Relación de aspecto, área segura y uso final | Rechazar formatos todavía no soportados |
| `visual_reference_urls` | Referencias autorizadas para dirección visual | Registrar origen y permisos; no copiar una pieza completa |

El constructor debe normalizar estos datos a una especificación similar a:

```json
{
  "subject": "personas aprendiendo inglés en un entorno ...",
  "audience": "...",
  "objective": "...",
  "mood": "...",
  "composition": "...",
  "visual_elements": ["..."],
  "aspect_ratio": "square",
  "text_policy": "leave clear text-safe areas; do not render final copy",
  "brand_constraints": {"pillar": "...", "allowed_colors": ["..."]}
}
```

El prompt final debe ordenar al modelo: crear una escena original, respetar la dirección de arte y reservar zonas limpias para el texto; no generar logos, nombres propios, precios, fechas, URLs, teléfonos ni claims. Todo texto final se añadirá después con tipografía y composición deterministas.

## 4. Restricciones de marca

Las restricciones no deben vivir solo en instrucciones libres del prompt. El futuro servicio debe cargar y versionar las fuentes de verdad existentes:

- `brand/tokens/colors.yaml`: paleta primaria, secundaria, neutros, rainbow y reglas de contraste.
- `brand/product-colors/authorized-colors.yaml`: color principal, secundario, fondo y CTA de cada uno de los seis pilares.
- `brand/assets/logos/manifest.yaml`: solo activos con `approved: true` y su variante, país, fondo permitido y regla de clear space.
- `brand/tokens/typography.yaml` y `brand/documentation/typography-rules.md`: Aptos para titulares y Open Sans para cuerpo; la licencia de redistribución de Aptos sigue abierta.
- `brand/documentation/logo-rules.md` y `accessibility-rules.md`: fondos permitidos, zona de exclusión, contraste y tamaños mínimos designados.

### Cómo inyectarlas

El prompt visual recibirá una sección de restricciones derivada de esos archivos, no una copia manual mantenida en código. Como mínimo incluirá:

1. Paleta autorizada para el pilar seleccionado, con HEX exactos y el límite de no mezclar colores principales de dos pilares.
2. Fondo y tratamiento de contraste permitidos.
3. Prohibición de gradientes de marca, salvo que una futura decisión de marca los autorice explícitamente.
4. Indicaciones de composición para dejar la zona de logo y la zona de texto libres.
5. Identificador del logo aprobado que se compondrá después; el modelo no dibuja ni modifica el artwork.
6. Tipografía que se aplicará después, nunca una instrucción para que el modelo la simule dentro de la imagen.

La estrategia recomendada es generar primero una imagen sin logo ni copy y componer ambos con activos aprobados. Así se evita el logo inventado, la tipografía deformada y la falsa precisión de pedirle al modelo que reproduzca un lockup institucional.

## 5. Validación automática antes de revisión humana

La imagen no debe llegar a revisión humana como si fuera válida solo porque la API respondió correctamente. El resultado debe pasar una cadena de validaciones, guardar un resumen en la versión y producir `passed`, `needs_review` o `rejected`.

### Validaciones deterministas

- formato, dimensiones, relación de aspecto y peso máximo;
- archivo decodificable, MIME esperado, checksum y almacenamiento seguro;
- existencia del logo referenciado en el manifest y `approved: true`;
- logo y copy compuestos fuera de los bordes y dentro de la safe zone;
- contraste del copy y logo contra el fondo, reutilizando los umbrales WCAG y el chequeo safe-zone existente;
- colores dominantes comparados contra la paleta permitida, con tolerancia documentada para fotografía, piel y elementos naturales que la guía permite conservar;
- ausencia de una segunda marca o un activo no autorizado en la composición final.

### Validaciones visuales/OCR

Un validador de visión y OCR, preferiblemente separado del generador, debe señalar:

- texto ilegible, texto deformado o texto inesperado dentro de la imagen base;
- presencia de un logo que no coincide con el asset aprobado;
- logo cortado, cambiado, de bajo contraste o fuera de su zona de exclusión;
- paleta visual claramente fuera de los colores del pilar;
- composición que oculta la zona reservada para copy/CTA;
- objetos, personas o claims visuales que no procedan del brief confirmado.

La revisión de visión es una señal de riesgo, no una autoridad para aprobar claims. Las reglas de datos confirmados siguen siendo deterministas: si un dato no está en el catálogo/campaña con estado confirmado, no se incorpora.

### Resultado y bloqueo

| Resultado | Comportamiento |
| --- | --- |
| `passed` | Puede entrar a revisión humana, nunca se autoaprueba |
| `needs_review` | Entra a revisión con advertencias visibles y no puede entregarse sin decisión humana |
| `rejected` | No se muestra como diseño utilizable; se conserva el motivo y se permite regenerar con control de costo |

El resumen debe conservar modelo, versión de reglas, umbrales, resultados por regla, referencia del artefacto y motivo de cualquier regeneración. Las llamadas al proveedor seguirán el sistema de auditoría de IA del proyecto cuando la integración se construya.

## 6. Convivencia con plantillas y rollout

El modo `template` seguirá siendo el default y la ruta de fallback explícita. El modo `ai_image` debe:

- estar detrás de una bandera de entorno y, si es necesario, una allowlist de usuarios o campañas de staging;
- reutilizar `DesignBrief`, `DesignVersion`, revisión y entrega;
- comenzar únicamente con formatos que ya tienen renderer y safe-zone verificables;
- conservar el artefacto original generado y la composición final por separado;
- limitar el número de regeneraciones por versión para controlar costo;
- permitir desactivación inmediata sin migrar ni invalidar diseños de plantillas;
- registrar qué modo produjo cada versión para que el historial no sea ambiguo.

No se recomienda reemplazar el renderer actual ni introducir imágenes generadas en todos los kits en el primer lanzamiento. Después de un piloto, se medirían tasa de rechazo, costo por versión aceptada, tiempo de revisión, legibilidad, consistencia de marca y tasa de regeneración antes de ampliar formatos o sedes.

## 7. Decisiones requeridas de Axel antes de implementar

La implementación queda bloqueada hasta acordar, en un solo punto de confirmación:

1. Modelo exacto y cuenta/proyecto OpenAI autorizados.
2. Presupuesto máximo por imagen y mensual, incluidos reintentos y validaciones.
3. Resoluciones y formatos iniciales; si se permite fotografía, ilustración o ambos.
4. Nivel de riesgo de marca aceptable y qué advertencias obligan a rechazo.
5. Regla de texto: recomendación actual, cero copy final dentro de la imagen generada.
6. Lista de logos y sub-marcas permitidos para el piloto, incluyendo tratamiento de co-branding.
7. Política de retención, uso de referencias y datos enviados al proveedor.
8. Qué ocurre si la imagen falla: regeneración limitada, retorno a plantilla o bloqueo para revisión manual.
9. Qué formato/pilar/campaña será el piloto y quién autoriza ampliar el rollout.

## 8. Fuera de alcance de esta fase

- No se añadió cliente de imágenes, endpoint, task, modelo, feature flag ni migración.
- No se modificó el renderer actual ni el flujo de plantillas.
- No se modificó `backend/security/` ni se activó SSO.
- No se eligió un modelo o presupuesto definitivo.
- No se permite todavía generar imágenes reales desde el producto.
