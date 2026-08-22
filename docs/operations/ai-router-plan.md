# Plan de arquitectura para AI Router multi-proveedor

**Estado:** diseño para revisión. No implementado.

**Fecha de referencia:** 2026-08-22.

**Objetivo:** evolucionar la integración de IA de `ih-design-platform` hacia un sistema
multi-proveedor que seleccione el motor adecuado por tarea, calidad, costo, velocidad,
disponibilidad y límites de uso, sin reemplazar el renderer, los flujos ni las integraciones
que ya funcionan.

Este documento no agrega dependencias, no activa proveedores, no cambia credenciales, no modifica
`backend/security/` y no forma parte de la certificación end-to-end en curso.

## 1. Resumen ejecutivo

La recomendación es crear en el futuro una capa de decisión pequeña entre los servicios de dominio
y los proveedores actuales. Esa capa no genera contenido por sí misma: filtra candidatos por
capacidades y políticas, prioriza opciones gratis/free-tier aprobadas para las tareas nuevas,
ejecuta cada intento a través de la auditoría existente y aplica un fallback controlado cuando el
error es técnico. OpenAI y Anthropic quedan como opciones premium o de continuidad para tareas
nuevas, no como consumo predeterminado cuando una alternativa gratuita validada cubra el caso.

La evolución debe conservar estas reglas:

1. `template` sigue siendo el modo predeterminado y seguro.
2. El router selecciona proveedores; la orquestación decide la secuencia de tareas.
3. `audited_generate()` o `record_visual_review()` registra cada intento real, incluido un
   fallback fallido. No se audita solamente el resultado final.
4. El contexto autorizado se construye y valida antes de seleccionar proveedor. Todos reciben
   exactamente el mismo contexto confirmado.
5. Las reglas deterministas de marca y el renderer controlado siguen teniendo autoridad sobre
   colores, logos, tipografía, safe-zone, copy y CTA.
6. Un fallback técnico nunca cambia silenciosamente `template` por `ai_image`, ni reduce una
   exigencia de privacidad, calidad o formato.
7. La comparación de múltiples motores y el uso de una IA como juez son opt-in para piezas
   importantes, no el comportamiento normal.
8. Un proveedor gratis no se considera elegible solo por precio: debe permitir el uso comercial,
   tener licencia de modelo aprobada, cumplir la política de datos y exponer límites operables.
9. Ningún fallback de una tarea nueva puede generar gasto por llamada sin una autorización
   explícita de fallback pagado y presupuesto disponible.

Orden recomendado de evaluación:

1. Congelar mediante pruebas el comportamiento de OpenAI y Anthropic que ya está en certificación.
2. Evaluar Groq free tier para tareas nuevas de texto breve y bajo riesgo.
3. Evaluar Cloudflare Workers AI con FLUX.2 `[klein]` 4B para la futura generación de imagen base.
4. Evaluar OpenRouter free solo como contingencia de bajo volumen, con modelo y backend fijados.
5. Evaluar Gemini free únicamente con datos sintéticos o públicos; no con briefs reales.
6. Mantener OpenAI y Anthropic como fallback/premium para tareas nuevas y como línea base de
   calidad, sin modificar sus puntos de llamada actuales.
7. No desplegar Ollama dentro de Railway con la infraestructura actual.

### 1.1 Cambio de prioridad, no migración

Esta decisión **no migra, sustituye ni apaga** el flujo construido. Los borradores de copy que hoy
usan OpenAI y la revisión automática que hoy usa Anthropic permanecen activos, con el mismo
contrato, configuración y comportamiento durante la certificación end-to-end. Tampoco se enrutan
retroactivamente por un proveedor gratuito.

La prioridad free-first se aplica solamente a tareas y proveedores que se incorporen después de
aprobar este plan. OpenAI y Anthropic siguen siendo válidos cuando:

- el punto de llamada existente ya está certificado con ese proveedor;
- el free tier principal falla, se satura o queda fuera de servicio y la política permite gasto;
- una tarea exige expresamente calidad premium certificada, como la revisión final antes de una
  entrega a cliente;
- una persona autorizada selecciona un modo premium y acepta su presupuesto.

La implementación futura debe distinguir `existing_certified_flow` de `new_routed_task`. El
primero conserva el proveedor actual; el segundo aplica la política free-first. Esto evita que un
cambio de arquitectura altere silenciosamente la certificación que está en curso.

## 2. Arquitectura que ya existe

### 2.1 Contrato general para generación

`backend/ai/providers/base.py` define:

- `GenerationRequest`: instrucción, `authorized_context` y formato esperado;
- `GenerationResponse`: proveedor, modelo, contenido y metadata;
- `AIProvider.generate()`: contrato síncrono común;
- `AIProviderError`: error traducible a un fallo del proveedor.

`OpenAIProvider` implementa este contrato y llama a Responses API. La integración actual fija una
instrucción de seguridad que prohíbe inventar precios, fechas, ubicaciones, contactos, hechos
académicos, logos y texto crítico dentro de imágenes.

Este contrato ya es suficiente para integrar proveedores de texto y respuestas estructuradas. Un
adaptador nuevo de Groq, Gemini u OpenRouter debe implementar exactamente `AIProvider` y devolver
`GenerationResponse`; los servicios de briefs, copy y revisión de copy no deberían conocer el SDK
ni el payload específico de cada proveedor.

### 2.2 La revisión visual usa un contrato especializado

Hay una diferencia importante respecto de la suposición de un único contrato: actualmente
`AnthropicVisualReviewProvider` no implementa `AIProvider.generate()`. Implementa
`VisualReviewProvider.review()`, definido en `backend/ai/services/design_review.py`, porque recibe
un `VisualReviewRequest` y devuelve un `VisualReviewResult` sometido a un JSON Schema con ocho
controles obligatorios.

No conviene eliminar ni reescribir este camino. El router futuro debe soportarlo mediante una de
estas dos opciones, en este orden de preferencia:

1. seleccionar un proveedor por capacidad y entregar un adaptador que implemente el contrato
   especializado `VisualReviewProvider`; o
2. envolver un proveedor general `AIProvider` en un `VisualReviewProviderAdapter` que construya y
   valide el mismo resultado estructurado.

Así se mantiene intacta la integración Anthropic, incluida la sanitización del SVG, el límite de
imagen, el schema, las transiciones de `DesignVersion` y el fallback explícito
`needs_confirmation`.

### 2.3 Auditoría universal ya disponible

`backend/ai/services/audit.py` contiene dos puntos de auditoría que deben seguir siendo la única
puerta de ejecución:

- `audited_generate()` para `AIProvider.generate()`;
- `record_visual_review()` para el contrato visual.

Actualmente registran proveedor, modelo, prompt/contexto, respuesta, metadata, resultado de
calidad, error, timestamp y vínculos con brief, versión o bundle. `AICallAudit.response_metadata`
ya puede alojar en el futuro, sin cambiar primero el modelo, información como:

- `route_id`;
- tipo de tarea;
- número de intento;
- razón de selección;
- latencia;
- costo estimado y real cuando el proveedor lo reporte;
- causa de fallback;
- estado de rate limit conocido.

El router no debe envolver toda la cadena en una sola auditoría. Cada llamada a un proveedor debe
pasar por `audited_generate()` o `record_visual_review()` para conservar la historia real.

### 2.4 Guardrail de datos confirmados

`backend/materials/services/ai_copy_drafts.py` muestra el patrón que debe generalizarse:

1. validar productos, sede, campaña, oferta y CTA;
2. excluir cualquier fuente no confirmada;
3. construir `authorized_context` mínimo;
4. enviar ese contexto al proveedor;
5. validar la respuesta contra las mismas fuentes, incluidas cifras y CTA;
6. guardar el resultado como borrador pendiente de aprobación.

El guardrail pertenece al dominio, no al proveedor. Debe ejecutarse antes y después del router y
no duplicarse dentro de cada adaptador. Un proveedor alternativo nunca obtiene información que el
proveedor principal no habría recibido.

### 2.5 Generación de imágenes ya diseñada

`docs/operations/ai-image-generation-plan.md` define `generation_mode = template | ai_image` y
mantiene `template` como predeterminado. El AI Router no cambia esa decisión. Solo seleccionaría
el motor cuando el usuario o la política ya hayan solicitado `ai_image`.

La imagen generada debe seguir siendo una base sin copy final ni logo. El renderer actual compone
posteriormente copy, CTA, tipografía y activos aprobados.

## 3. Arquitectura propuesta

### 3.1 Componentes conceptuales

La implementación futura puede dividirse en seis piezas pequeñas:

```text
Servicio de dominio
  -> guardrail de datos confirmados
  -> política de tarea
  -> AI Router
       -> registro de capacidades
       -> presupuesto/cuotas
       -> salud y circuit breaker
       -> proveedor seleccionado
  -> audited_generate() / record_visual_review()
  -> validador determinista de salida
  -> persistencia y flujo humano existentes
```

| Componente | Responsabilidad | No debe hacer |
| --- | --- | --- |
| `AITaskPolicy` | Declara requisitos duros y preferencias de una tarea | Llamar APIs |
| `AIProviderRegistry` | Registra proveedor, modelo y capacidades | Decidir por contenido del brief |
| `AIRouter` | Filtra, puntúa y ordena candidatos | Construir prompts o validar marca |
| `routed_generate()` | Ejecuta candidatos usando `audited_generate()` | Saltarse auditoría |
| Adaptadores | Traducen el contrato común al API específico | Aplicar reglas de negocio propias |
| Orquestador | Encadena tareas y conserva estado | Elegir SDKs directamente |

No es necesario introducir todos estos nombres o clases en la primera fase; describen límites de
responsabilidad, no una obligación de estructura exacta.

### 3.2 Tipos de tarea

El router necesita una señal explícita y estable, por ejemplo:

```text
brief_interpretation
prompt_improvement
copy_generation
image_generation
visual_review
quality_judge
```

El tipo de tarea no debe inferirse buscando palabras dentro del prompt. Lo declara el servicio de
dominio que ya conoce la operación.

Cada solicitud de routing incluiría, conceptualmente:

- tipo de tarea;
- formato/modalidad requerida: texto, JSON, imagen de entrada o imagen de salida;
- nivel de calidad: `economy`, `standard` o `premium`;
- latencia objetivo;
- costo máximo por intento y por flujo;
- requisitos de privacidad/retención;
- necesidad de output estructurado;
- proveedor/modelo forzado, si una decisión humana lo exige;
- lista de proveedores excluidos;
- si se permite fallback y cuántos intentos.

`GenerationRequest` sigue conteniendo el contenido autorizado. La política de routing debe viajar
separada para no mezclar datos de negocio con decisiones de infraestructura.

### 3.3 Registro de capacidades

Cada proveedor/modelo se registra con metadata configurada y verificable:

```text
modalities: text_input, image_input, text_output, image_output
structured_output: true | false
task_allowlist: [...]
quality_tier: economy | standard | premium
estimated_input_cost
estimated_output_cost
expected_latency
production_status: production | preview | evaluation
privacy_policy: paid_no_training | zdr | review_required
commercial_use: approved | conditional | blocked
billing_mode: free_hard_cap | free_then_billed | paid
paid_fallback_allowed: true | false
```

La disponibilidad de un modelo no debe estar hardcodeada como verdad permanente. Los modelos
preview, deprecados o con licencia no aprobada deben deshabilitarse desde configuración.

### 3.4 Algoritmo de selección

Para cada tarea:

1. **Filtrar requisitos duros:** modalidad, JSON Schema, tamaño de imagen, privacidad, modelo en
   producción, región y licencia.
2. **Excluir proveedores no configurados:** sin credencial o marcados como inactivos.
3. **Verificar elegibilidad comercial y de datos:** licencia del modelo, términos de producción,
   retención, región y sensibilidad del contexto.
4. **Consultar presupuesto y cuotas:** priorizar candidatos `free_hard_cap`; descartar candidatos
   que excedan el costo máximo o estén en cooldown por `429`/límite de gasto.
5. **Bloquear gasto no autorizado:** un candidato pagado solo entra si es un flujo certificado
   existente, una tarea `premium` o `paid_fallback_allowed=true` con presupuesto.
6. **Puntuar candidatos:** calidad esperada, costo, latencia y salud reciente con pesos de la
   política de tarea. Para tareas nuevas compatibles, costo cero aprobado tiene prioridad.
7. **Seleccionar y registrar la razón:** proveedor/modelo elegido y alternativas elegibles.
8. **Ejecutar mediante la auditoría actual.**
9. **Validar la salida:** contrato, datos confirmados y reglas de marca.
10. **Aplicar fallback solamente ante errores elegibles.**

Ejemplo de políticas iniciales, sujeto a benchmark:

| Tarea | Primario propuesto | Fallback | Motivo |
| --- | --- | --- | --- |
| Interpretar brief, tarea nueva | Groq free con modelo aprobado | OpenRouter free fijado; OpenAI solo si se autoriza gasto | Texto rápido y JSON con guardrail posterior |
| Mejorar prompt/copy, tarea nueva | Groq free con modelo aprobado | OpenRouter free fijado; OpenAI solo si se autoriza gasto | Evitar consumo pagado predeterminado |
| Borrador de copy actual | OpenAI actual, sin cambio | Comportamiento actual | Flujo construido y en certificación; fuera de la migración |
| Generar imagen base, tarea futura | Cloudflare Workers AI con FLUX.2 `[klein]` 4B aprobado | OpenAI Images solo en modo premium autorizado | Solo cuando `ai_image` esté habilitado |
| Revisión visual actual | Anthropic actual, sin cambio | `needs_confirmation` actual | Flujo construido y en certificación |
| Revisión multimodal experimental | Gemini free solo con datos sintéticos/públicos | Ninguno automático | Evaluación, nunca fallback de producción |
| Juez premium | Anthropic/OpenAI certificado, modelo fijado | Ninguno por defecto | Solo en `premium_compare` y con presupuesto |

La tabla expresa un orden de evaluación, no una selección aprobada.

### 3.5 Fallback y circuit breaker

Se permite fallback automático para:

- timeout;
- error 5xx;
- `429` o cuota agotada;
- proveedor/modelo temporalmente no disponible;
- respuesta imposible de decodificar o fuera del contrato después de un reintento limitado.

No se permite fallback automático para:

- rechazo por política de seguridad;
- datos no confirmados;
- fallo de marca determinista;
- falta de permiso del usuario;
- presupuesto agotado del flujo;
- cambio de `template` a `ai_image` o viceversa;
- sustitución por un proveedor con política de datos menos restrictiva;
- respuesta válida pero creativamente insatisfactoria en modo normal.

Un proveedor que acumule fallos elegibles entra en un circuit breaker temporal. La recuperación se
prueba con llamadas controladas; no se envía continuamente tráfico real a un proveedor caído.

El número recomendado de intentos para el modo normal es:

- un intento principal;
- un reintento breve solo si el error es transitorio y la llamada es idempotente;
- un proveedor alternativo como máximo.

Para tareas nuevas, `paid_fallback_allowed` debe ser `false` por defecto. Un `429` del free tier
puede activar otro candidato gratuito aprobado; solo puede llegar a OpenAI o Anthropic si la tarea
está marcada como premium o una política autorizada habilita expresamente el gasto. El router no
debe registrar una tarjeta o cambiar un proyecto a pago como efecto de un fallback.

Cada intento consume presupuesto y queda auditado. Si todos fallan, el sistema conserva el estado
de error/pendiente ya utilizado por los flujos actuales y muestra una causa accionable.

## 4. Conservación universal de auditoría y guardrails

### 4.1 Ejecución de texto

Un futuro `routed_generate()` debe obtener la lista ordenada del router y llamar, por candidato:

```text
audited_generate(provider, generation_request, brief/design_version/material_bundle)
```

De esta manera no cambia el contrato de `OpenAIProvider`, y las futuras implementaciones de Groq,
Gemini u OpenRouter entran por la misma ruta.

### 4.2 Revisión visual

El router devuelve un proveedor compatible con `VisualReviewProvider`, nativo o adaptado. La
ejecución sigue pasando por `run_automatic_design_review()` y `record_visual_review()`. El schema,
los ocho checks y las transiciones actuales no se replican dentro de Gemini u otro proveedor.

### 4.3 Imágenes

Para respetar el contrato de `base.py` sin guardar binarios gigantes en `content`, un adaptador de
imágenes puede implementar `AIProvider.generate()` y devolver un descriptor JSON serializado:

```json
{
  "artifact_ref": "storage-key-or-temporary-reference",
  "mime_type": "image/png",
  "width": 1024,
  "height": 1024,
  "checksum": "..."
}
```

`GenerationResponse.metadata` conservaría el identificador del proveedor, parámetros y métricas.
El servicio de imágenes validaría el descriptor y almacenaría el archivo siguiendo
`ai-image-generation-plan.md`. Si durante el spike técnico este encaje resulta artificial, puede
definirse un protocolo especializado de imagen y envolverlo con un adaptador, igual que ya ocurre
con revisión visual. No se debe alterar `AIProvider` hasta demostrar que el contrato actual es
insuficiente.

### 4.4 Invariantes de datos y marca

Estas validaciones se ejecutan sin importar el proveedor:

- solo catálogo, campaña, sede y CTA confirmados;
- bloqueo de cifras, URLs y claims no autorizados;
- output estructurado validado antes de persistir;
- colores obtenidos de los tokens y paletas por producto;
- logos únicamente del manifest aprobado;
- logo y copy compuestos por el renderer, no por el modelo de imagen;
- safe-zone, márgenes, contraste, dimensiones y legibilidad deterministas;
- revisión visual como señal adicional, nunca sustituto de las reglas o la aprobación humana.

## 5. Candidatos a evaluar

Los precios y límites siguientes son una fotografía al 2026-08-22. Deben verificarse de nuevo al
aprobar una integración porque modelos, cuotas y precios cambian.

### 5.1 Groq

**Encaje:** texto rápido, interpretación de brief, normalización JSON, clasificación y mejora de
prompts para tareas nuevas. Es el primer candidato free-first para texto. Expone una API compatible
con OpenAI y sus modelos de producción publicados destacan por alto throughput.

**Ventajas:**

- latencia muy baja;
- modelos de producción económicos;
- integración sencilla detrás de `AIProvider`;
- headers de rate limit y `retry-after` útiles para routing;
- límites de gasto en cuentas pagadas.

**Límites/riesgos:**

- no es el candidato para generación de imagen;
- la calidad depende del modelo abierto seleccionado;
- los modelos preview pueden desaparecer y no deben entrar a producción;
- la licencia y uso comercial deben comprobarse por modelo, no solo por plataforma.

Como referencia, `openai/gpt-oss-120b` aparece como modelo de producción a **USD 0.15/M tokens de
entrada y USD 0.60/M de salida**, con 500 tokens/s publicados. En free tier, su límite publicado es
**30 RPM, 1,000 RPD, 8,000 TPM y 200,000 TPD**. Al excederlo, la API responde `429` e incluye
`retry-after`: es bloqueo temporal, no degradación de modelo. La cuenta free debe cambiarse
explícitamente al Developer tier y registrar un método de pago; no hay cobro automático por el
simple hecho de alcanzar la cuota gratuita.

**Uso comercial:** viable con condición. El acuerdo de Groq gobierna servicios para desarrolladores,
empresas y organizaciones, y define uso preview o de producción. Sin embargo, obliga a revisar los
términos de cada modelo. Para este candidato concreto, OpenAI publica `gpt-oss-120b` bajo Apache 2.0
con uso comercial. Antes de activarlo se deben volver a verificar ambos documentos y el AUP.

**Conclusión:** candidato principal para texto nuevo de bajo riesgo, incluso en producción de bajo
volumen, pero sin SLA de capacidad en free tier. El router debe vigilar RPD/TPD y cambiar a otro
proveedor gratuito antes de permitir un fallback pagado.

Fuentes: [modelos y precios de Groq](https://console.groq.com/docs/models),
[límites](https://console.groq.com/docs/rate-limits),
[billing FAQ](https://console.groq.com/docs/billing-faqs),
[acuerdo de servicios](https://console.groq.com/docs/legal/services-agreement) y
[licencia de gpt-oss](https://openai.com/index/introducing-gpt-oss/).

### 5.2 Gemini

**Encaje limitado:** evaluación de razonamiento y revisión multimodal con materiales sintéticos o
públicos. Gemini pagado queda fuera de esta propuesta por decisión de Axel.

**Ventajas:**

- texto e imagen en una misma familia;
- output estructurado y contexto amplio;
- capacidad técnica para contrastar, en laboratorio, la revisión Anthropic actual.

**Límites/riesgos:**

- Google no publica una cifra universal vigente de RPM/TPM/RPD: la cuota efectiva se consulta por
  proyecto en AI Studio y puede variar por modelo, tier y cuenta;
- Google usa prompts y respuestas del servicio gratuito para mejorar sus productos y permite que
  revisores humanos los lean, anoten y procesen;
- los términos indican que no se envíe información sensible, confidencial ni personal al servicio
  gratuito; un brief real puede contener precisamente esos datos;
- previews/experimentales tienen límites más bajos y estabilidad menor;
- un resultado multimodal válido todavía debe pasar el schema y controles deterministas locales.

**Uso comercial:** no se encontró en los términos vigentes una autorización específica que declare
el unpaid tier apto para producción comercial, aunque tampoco una prohibición general de construir
una aplicación comercial. Esa ambigüedad no debe resolverse a favor del proveedor. Además, la
restricción práctica es más fuerte: fuera de la excepción publicada para EEE, Suiza y Reino Unido,
no deben enviarse datos sensibles, confidenciales ni personales al unpaid service. IH LATAM no debe
basar un flujo productivo real en esa excepción geográfica.

Al superar la cuota, la API responde **HTTP 429 `RESOURCE_EXHAUSTED`** y se debe esperar/reintentar o
solicitar una cuota mayor. Un proyecto gratuito no empieza a cobrar automáticamente; habilitar Cloud
Billing es la acción explícita que lo mueve al tier pagado. Como la documentación oficial vigente
remite la cifra exacta al panel de AI Studio, este plan no inventa un número fijo.

**Conclusión:** Gemini free es técnicamente capaz de revisión multimodal, pero queda clasificado
`evaluation_only`; no es proveedor de producción, no recibe briefs/diseños reales y no participa en
fallback automático. Si en el futuro se reconsidera el tier pagado, será una decisión separada.

Fuentes: [precios y política por tier](https://ai.google.dev/gemini-api/docs/pricing),
[términos adicionales](https://ai.google.dev/gemini-api/terms),
[rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) y
[errores de API](https://ai.google.dev/gemini-api/docs/troubleshooting).

### 5.3 OpenRouter

**Encaje:** contingencia free de bajo volumen para tareas nuevas de texto y experimentación con una
API unificada. No sustituye al router interno.

**Ventajas:**

- API compatible con OpenAI;
- orden de proveedores, fallbacks, precio máximo, latencia, throughput y ZDR configurables;
- agrega disponibilidad de múltiples backends;
- permite probar modelos sin integrar cada facturación desde el primer día.

**Límites/riesgos:**

- introduce un intermediario adicional y sus propios metadatos, políticas y facturación;
- puede duplicar las responsabilidades del AI Router interno;
- calidad, retención y licencia siguen dependiendo del modelo y endpoint final;
- la selección dinámica puede reducir reproducibilidad si no se fija modelo/proveedor;
- cobra una comisión al comprar créditos aunque pase el precio de inferencia sin markup.

El plan free publica **50 requests/día**; con al menos USD 10 en créditos comprados, los modelos
free llegan a **1,000 requests/día**. Al superar la cuota devuelve un error de rate limit/`429`; no
convierte por sí solo la solicitud a un modelo pagado. Un fallback configurado expresamente sí puede
usar otro modelo, y entonces se factura el modelo finalmente ejecutado. En pay-as-you-go, el costo
es el del modelo subyacente y existe una comisión de compra de créditos de **5.5% con mínimo de USD
0.80**.

**Uso comercial:** viable con condición. Los términos contemplan incorporar el servicio en
productos propios y dar acceso a clientes, pero cada `Model Terms` controla licencia, uso de inputs
y propiedad/uso de outputs. No existe una autorización comercial única para todo el catálogo free.
El router `openrouter/free`, que elige aleatoriamente entre modelos disponibles y puede cambiar con
el tiempo, no es aceptable para producción de marca.

Recomendación: mantenerlo como segundo candidato gratuito para continuidad de bajo volumen. Exigir
modelo fijado, términos comerciales aprobados, `zdr=true`, `data_collection=deny`, lista de
proveedores aprobados y metadata completa. Si ninguna ruta free fijada está disponible, fallar de
forma explícita salvo que `paid_fallback_allowed=true`.

Fuentes: [FAQ/precios](https://openrouter.ai/docs/faq),
[términos](https://openrouter.ai/terms),
[free model router](https://openrouter.ai/docs/guides/routing/routers/free-router),
[errores y rate limits](https://openrouter.ai/docs/api/api-reference/responses/create-responses),
[fallbacks y facturación](https://openrouter.ai/docs/guides/routing/model-fallbacks),
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) y
[Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr).

### 5.4 Cloudflare Workers AI / FLUX

**Encaje:** primer candidato free-first para generar la imagen base dentro de
`generation_mode=ai_image`; no debe componer logos ni copy final.

**Ventajas:**

- modelos FLUX con costos bajos y facturación serverless;
- free allocation diaria útil para spikes controlados;
- Cloudflare declara que no usa Customer Content para entrenar o mejorar modelos/servicios sin
  consentimiento explícito;
- buena separación entre Railway, que orquesta, y Cloudflare, que aporta GPU administrada.

**Límites/riesgos:**

- modelos distintos tienen fórmulas de precio, pasos y calidad diferentes;
- el modelo subyacente puede tener términos/licencia propios;
- el free allocation no es una garantía de capacidad y las operaciones fallan al agotarse;
- se añade otra cuenta, credencial, observabilidad y superficie de incidentes.

Workers AI incluye **10,000 Neurons/día** sin costo. En Workers Free, al agotarse la asignación las
operaciones fallan con **HTTP 429 / código 3036** hasta el reset diario o hasta que la cuenta cambie
de plan: no hay cobro automático. En Workers Paid, la misma asignación gratuita se conserva y el
exceso se cobra automáticamente a **USD 0.011 por 1,000 Neurons**. El límite publicado para tareas
text-to-image es **720 RPM** por defecto; modelos beta pueden tener límites menores.

Ejemplos oficiales:

- `flux-1-schnell`: USD 0.0000528 por tile 512x512 y USD 0.0001056 por paso;
- `flux-2-klein-4b`: USD 0.000059 por tile de entrada y USD 0.000287 por tile de salida;
- `flux-2-klein-9b`: USD 0.015 por el primer megapíxel;
- `flux-2-dev`: USD 0.00041 por tile de salida 512x512 por paso, además de cualquier entrada.

**Uso comercial:** viable con condición y revisión por modelo. Cloudflare indica que cada modelo
de terceros conserva sus términos. Para el primer piloto se recomienda limitar el candidato a
`@cf/black-forest-labs/flux-2-klein-4b`: Black Forest Labs publica esa variante bajo Apache 2.0 con
uso comercial gratuito. No se debe extrapolar esa autorización a `[klein]` 9B o `flux-2-dev`, cuyas
weights están bajo licencia no comercial. Antes de producción debe verificarse además el model card
específico servido por Cloudflare.

El costo real debe calcularse con resolución, pasos e imágenes de referencia aprobados. No se debe
elegir el motor solo por el menor costo: primero debe pasar el benchmark de calidad de marca. El
primer despliegue debe permanecer en Workers Free para que el límite sea duro; pasar a Workers Paid
requiere una decisión separada porque convertiría el exceso en cobro automático.

Fuentes: [precios de Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/),
[límites](https://developers.cloudflare.com/workers-ai/platform/limits/),
[errores](https://developers.cloudflare.com/workers-ai/platform/errors/),
[acuerdo self-serve de Cloudflare](https://www.cloudflare.com/terms/),
[modelos](https://developers.cloudflare.com/workers-ai/models/) y
[uso de datos](https://developers.cloudflare.com/workers-ai/platform/data-usage/), además de la
[licencia de FLUX.2 klein](https://help.bfl.ai/articles/7108141705-can-i-run-or-fine-tune-flux-2-klein-locally).

### 5.5 Ollama

**Encaje posible:** desarrollo local, pruebas sin enviar datos a una API externa o un servicio
separado con GPU propia. No es viable como proveedor de producción dentro de Railway actualmente.

La etiqueta “sin costo por llamada” es engañosa para esta arquitectura:

- Railway declara que no ofrece instancias GPU y recomienda no servir ni modelos pequeños sobre
  CPU;
- un modelo relativamente pequeño como Gemma 3 4B ocupa aproximadamente 3.3 GB solo como archivo;
- Llama 3.1 8B ocupa aproximadamente 4.9 GB y los modelos mayores requieren 43 GB o más;
- la memoria de ejecución, el contexto y el proceso de Ollama se suman al tamaño del modelo;
- en Railway, 8 GB de RAM usados de forma continua equivalen aproximadamente a USD 80/mes, antes
  de CPU; 1 vCPU continua añade aproximadamente USD 20/mes según la tarifa publicada;
- la inferencia CPU tendría latencia y throughput impredecibles, además de competir con el worker.

Por tanto, Ollama no es costo cero: cambia gasto por token por compute persistente, operación,
volumen, arranque y degradación de rendimiento. Solo debe reconsiderarse si IH dispone de una
máquina con GPU, un proveedor GPU externo o un caso offline que justifique operarla.

Fuentes: [Railway: Hosted Inference](https://docs.railway.com/guides/ai-api-hosted-inference),
[precios de Railway](https://docs.railway.com/pricing),
[soporte de hardware de Ollama](https://docs.ollama.com/gpu),
[Gemma 3](https://ollama.com/library/gemma3/tags) y
[Llama 3.1](https://ollama.com/library/llama3.1/tags).

### 5.6 OpenAI

**Encaje:** continuidad del comportamiento actual, salida estructurada, fallback de calidad y
opción premium. La primera versión del router debe reutilizar `OpenAIProvider` sin modificarlo. En
tareas nuevas no es el primario por defecto: se elige cuando la calidad/política lo exige o cuando
un fallback pagado fue autorizado.

**Ventajas:**

- ya está integrado y auditado;
- `gpt-4.1-mini` soporta Responses API, structured outputs e image input;
- snapshots permiten fijar comportamiento;
- sirve como referencia para medir cualquier candidato nuevo.

**Límites/riesgos:**

- requiere billing; el modelo actual no tiene tier API gratuito;
- usar OpenAI para cada etapa de una cadena aumenta costo y dependencia;
- la generación de imágenes necesita un adaptador distinto y aprobación del modelo exacto.

El modelo configurado actualmente, `gpt-4.1-mini`, publica **USD 0.40/M tokens de entrada y USD
1.60/M de salida**. La tarifa gratuita no está soportada para ese modelo. Para imagen, el modelo
vigente `GPT-Image-2` publica USD 8/M image-input tokens y USD 30/M image-output tokens, además de
USD 5/M tokens de entrada de texto; el costo por pieza depende de la tokenización y debe obtenerse
con el calculador oficial. Como referencia comparable por imagen, el modelo anterior
`gpt-image-1.5` publica para 1024x1024 USD 0.009 en calidad baja, USD 0.034 media y USD 0.133 alta.

Esto también revela una desactualización puntual en `ai-image-generation-plan.md`: allí
`GPT Image 2` figuraba como hipótesis no verificada. Al 2026-08-22 sí aparece en la documentación
oficial como `GPT-Image-2`. Este plan no modifica el documento anterior ni autoriza el modelo; la
decisión futura deberá reconciliar ambos documentos y verificar acceso en la cuenta real.

Fuentes: [`gpt-4.1-mini`](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[`gpt-image-1.5`](https://developers.openai.com/api/docs/models/gpt-image-1.5) y
[precios de API](https://openai.com/api/pricing/).

### 5.7 Anthropic como línea base existente

Anthropic no es una integración candidata nueva: ya es el revisor visual y ese flujo no cambia.
Debe permanecer como línea base en cualquier benchmark y puede conservarse como opción premium para
la revisión final previa a cliente. No puede presupuestarse una llamada concreta hasta que Axel
seleccione `ANTHROPIC_MODEL`, porque actualmente el setting no tiene un modelo por defecto.

El router no debe sustituirlo por Gemini free. Además del benchmark pendiente, los términos del
unpaid service de Gemini impiden tratarlo como destino apropiado para briefs reales de IH. Primero
se necesita un set sintético o público de diseños aprobados/rechazados por humanos y comparar
precisión, falsos positivos, omisiones y consistencia de los ocho controles actuales.

Fuente: [precios oficiales de Claude API](https://platform.claude.com/docs/en/about-claude/pricing).

## 6. Costos ilustrativos por tarea

Estos cálculos sirven para comparar órdenes de magnitud, no como presupuesto contractual.

Supuestos:

- tarea breve de texto: 2,000 tokens de entrada y 500 de salida;
- revisión multimodal: 4,000 tokens de entrada equivalentes y 800 de salida;
- imagen: 1024x1024, sin contar almacenamiento, egress, reintentos ni revisión;
- USD antes de impuestos;
- no se aplica prompt caching ni batch.

| Proveedor/modelo de referencia | Texto breve | Revisión multimodal | Imagen 1024x1024 | Lectura operativa |
| --- | ---: | ---: | ---: | --- |
| Groq free, `gpt-oss-120b` | USD 0 mientras haya cuota | No recomendado para este caso | No aplica | Primario propuesto para texto nuevo; 30 RPM/1,000 RPD |
| Gemini free | USD 0 mientras haya cuota | USD 0, cuota exacta por proyecto* | No evaluada aquí | Solo evaluación sintética/pública; no producción IH |
| OpenAI `gpt-4.1-mini` | ~USD 0.0016 | ~USD 0.00288 | No genera imagen por sí mismo | Referencia actual de texto/fallback |
| OpenRouter free fijado | USD 0 hasta 50 RPD; 1,000 RPD con créditos | Variable por modelo | Variable | Contingencia de bajo volumen, no router aleatorio |
| Cloudflare `flux-2-klein-4b` | No aplica | No aplica | USD 0 mientras haya Neurons | Primario propuesto; ~95 imágenes 1024x1024/día** |
| Cloudflare `flux-1-schnell` | No aplica | No aplica | USD 0 mientras haya Neurons | Alternativa de benchmark; licencia por confirmar |
| OpenAI `GPT-Image-2` | No aplica | No aplica | Variable por image tokens | Modelo vigente; usar calculador oficial |
| OpenAI `gpt-image-1.5` anterior | No aplica | No aplica | USD 0.009 / 0.034 / 0.133 | Baja/media/alta; verificar modelo vigente |
| Ollama en Railway | USD 0 marginal por request | Limitado por hardware | No práctico | ~USD 100+/mes de compute ilustrativo, sin GPU |

\* Gemini no publica una cuota universal vigente; debe leerse en AI Studio. La tokenización de
imágenes puede consumir cuota adicional.

\** Estimación matemática: 10,000 Neurons / (4 tiles de salida × 26.05 Neurons). No es garantía de
capacidad, no considera inputs, reintentos ni otros usos de la cuenta.

La cifra multimodal de OpenAI también es ilustrativa: la tokenización real de imágenes y el
reasoning pueden elevar el total.

Para estimar presupuesto mensual debe medirse primero un piloto real con el tamaño promedio de
prompts, outputs, imágenes y tasa de reintentos del proyecto. La métrica útil no es solo “costo por
llamada”, sino **costo por pieza aceptada**.

## 7. Free tiers y uso en producción

| Proveedor | ¿Uso comercial en producción? | Límite gratis verificado | Al superar el límite | Decisión para IH |
| --- | --- | --- | --- | --- |
| Groq + `gpt-oss-120b` | Sí, condicionado al acuerdo Groq y términos del modelo; gpt-oss es Apache 2.0 | 30 RPM, 1,000 RPD, 8K TPM, 200K TPD | HTTP 429 + `retry-after`; sin cobro automático, upgrade explícito | Primario para texto nuevo de bajo riesgo; sin asumir SLA |
| OpenRouter + modelo free fijado | Sí, condicionado a los términos de cada modelo; no hay permiso global del catálogo | 50 RPD; 1,000 RPD después de comprar al menos USD 10 en créditos | Error de rate limit/429; no cobra salvo fallback pagado configurado | Segundo candidato gratis de bajo volumen; prohibido `openrouter/free` aleatorio en producción |
| Cloudflare Workers AI + FLUX.2 `[klein]` 4B | Sí con revisión final; variante 4B Apache 2.0 y Cloudflare exige respetar términos del modelo | 10,000 Neurons/día y 720 RPM text-to-image por defecto | Workers Free: HTTP 429/3036 y bloqueo; Workers Paid: cobra automáticamente el exceso | Primario futuro de imagen en Workers Free; no pasar a Paid sin aprobación |
| Gemini free | No confirmado explícitamente como apto para producción comercial; sus reglas de datos lo vuelven inadecuado para briefs reales | Cuota exacta variable por proyecto/modelo; Google remite a AI Studio | HTTP 429 `RESOURCE_EXHAUSTED`; sin cobro hasta habilitar billing | Solo evaluación sintética/pública; no producción ni fallback automático |
| OpenAI API | Sí bajo el contrato aplicable; no hay free tier para el modelo actual | Ninguno para `gpt-4.1-mini` | Se factura conforme al tier/límites configurados | Flujo actual intacto; fallback/premium para tareas nuevas |
| Anthropic API | Sí bajo el contrato aplicable; no se presupone free tier de producción | No aplica en este plan | Se factura conforme al tier/límites configurados | Revisión actual intacta; premium/final para tareas nuevas |
| Ollama | Depende de la licencia del modelo | Sin tarifa API | Se agota el compute propio, no una cuota externa | No viable en Railway actual |

El uso comercial no debe deducirse de que exista un free tier. Antes de habilitar un modelo se
deben aprobar términos de servicio, licencia del modelo, retención, entrenamiento, región y
propiedad/uso de outputs. Esto es especialmente importante en agregadores y modelos abiertos. Las
cifras anteriores son una fotografía al 2026-08-22: una prueba previa al rollout debe consultar de
nuevo las URLs oficiales y registrar la cuota efectiva de las cuentas reales de IH.

## 8. Flujos colaborativos

### 8.1 Orquestación normal

La cadena se diseña por encima del router:

```text
Brief confirmado
  -> interpretar brief
  -> mejorar/estructurar prompt
  -> generar imagen base (solo si ai_image)
  -> componer marca/copy con renderer determinista
  -> validaciones deterministas
  -> revisión multimodal
  -> refinamiento limitado si hace falta
  -> revisión humana y entrega existentes
```

Responsabilidades:

1. **Interpretación:** transforma respuestas del brief en una intención estructurada sin añadir
   datos.
2. **Mejora de prompt:** convierte esa intención en dirección visual/copy manteniendo
   `authorized_context`.
3. **Generación:** produce una imagen base, no un arte final con logo o texto.
4. **Composición:** usa el renderer actual para controlar identidad y legibilidad.
5. **Revisión multimodal:** evalúa la versión final, no solo la imagen base.
6. **Refinamiento:** ajusta una instrucción concreta; nunca entra en bucle ilimitado.

Cada etapa tiene su propia política y puede elegir un proveedor diferente. El orquestador guarda
el estado entre etapas en PostgreSQL y ejecuta tareas largas mediante Celery, reutilizando la
infraestructura ya certificada. Un fallo no obliga a reiniciar toda la cadena si los artefactos
anteriores siguen siendo válidos.

Límites iniciales recomendados:

- máximo una regeneración automática;
- presupuesto total por flujo;
- timeout por etapa;
- cancelación explícita;
- no autoaprobar;
- no entregar mientras una validación determinista o humana esté pendiente.

### 8.2 Comparación multi-motor para piezas importantes

Agregar un modo opt-in:

```text
quality_mode = standard | premium_compare
```

`standard`:

- un proveedor elegido;
- fallback solo por fallo técnico;
- una generación normal;
- revisión actual.

`premium_compare`:

1. valida un presupuesto mayor y permiso del usuario;
2. genera dos o, como máximo, tres candidatos con motores/modelos distintos;
3. aplica las mismas validaciones deterministas a todos;
4. descarta candidatos inválidos antes de llamar al juez;
5. entrega al juez candidatos anonimizados, sin revelar el proveedor para reducir sesgo;
6. exige un score estructurado por composición, marca, legibilidad y alineación al brief;
7. conserva todos los candidatos, decisión y costos en auditoría;
8. muestra el ganador como recomendación, no como aprobación humana.

El juez no debe escoger entre candidatos que violan reglas deterministas. Si todos fallan, el
resultado es `needs_review` o `failed`, no “el menos malo”.

Para controlar costos:

- el modo nunca es default;
- solo roles autorizados pueden solicitarlo;
- se muestra costo estimado antes de ejecutar;
- tiene límite mensual y por pieza;
- no usa más de tres candidatos;
- no repite la comparación automáticamente;
- puede usar un juez económico después de filtrar localmente, si su precisión fue validada.

## 9. Riesgos y mitigaciones

### 9.1 Fragmentación de calidad de marca

**Riesgo:** distintos proveedores interpretan tono, personas, fondos y jerarquía de forma desigual.

**Mitigación:** benchmark versionado con piezas reales, modelos fijados, composición final
determinista y las mismas reglas de marca después de cualquier proveedor.

### 9.2 Fallback que cambia el resultado sin visibilidad

**Riesgo:** una caída produce silenciosamente una pieza con otro estilo/modelo.

**Mitigación:** auditar proveedor/modelo/intento, mostrar fallback en metadata y no usar fallback
creativo en modo normal; solo técnico.

### 9.3 Costos multiplicados

**Riesgo:** cadenas, reintentos, jueces y comparaciones elevan costo por pieza.

**Mitigación:** presupuesto por etapa/flujo/mes, máximo de intentos, estimación previa, circuit
breaker y métrica de costo por pieza aceptada.

### 9.4 Privacidad y retención inconsistentes

**Riesgo:** un agregador o endpoint alternativo tiene políticas distintas.

**Mitigación:** privacidad como requisito duro, no como preferencia; allowlist de proveedores,
ZDR cuando aplique, exclusión de Gemini free para datos reales y prohibición de degradar políticas
durante fallback.

### 9.5 Modelos y precios cambiantes

**Riesgo:** aliases cambian de comportamiento o un preview desaparece.

**Mitigación:** snapshots/versiones fijadas, registro configurable, revisión periódica de precios,
fecha de vigencia y desactivación sin deploy cuando sea posible.

### 9.6 Doble capa de routing

**Riesgo:** usar OpenRouter con fallbacks internos más el router de IH dificulta explicar qué
ocurrió.

**Mitigación:** si se habilita OpenRouter, tratarlo como un adaptador. En producción, fijar
modelo/proveedores permitidos y conservar en auditoría el proveedor final reportado.

### 9.7 Validación multimodal tomada como verdad

**Riesgo:** una IA revisora aprueba un logo, claim o safe-zone incorrectos.

**Mitigación:** verificaciones deterministas primero; la IA solo agrega una señal visual. La
aprobación humana y las reglas documentadas conservan autoridad.

## 10. Métricas para decidir proveedores

Cada candidato debe probarse contra el mismo conjunto de briefs y diseños ya aprobados. Medir:

- porcentaje de respuestas que cumplen schema;
- cifras/claims no autorizados;
- precisión y recall de hallazgos visuales;
- falsos positivos de revisión;
- tasa de aceptación humana sin cambios;
- latencia p50/p95;
- costo por llamada y por pieza aceptada;
- fallos, `429`, timeouts y fallbacks;
- estabilidad entre ejecuciones;
- consistencia de tono, colores y composición.

No se promueve un proveedor por un único ejemplo visual. El benchmark debe separar tareas: un
motor puede ganar en copy rápido y perder en revisión visual.

## 11. Roadmap de implementación futura

Este roadmap no autoriza implementación; define el orden si Axel aprueba el plan.

### Fase A — Router sin cambio de comportamiento

- registro de OpenAI y Anthropic actuales;
- políticas explícitas por los puntos de llamada existentes;
- mismo proveedor/modelo que hoy;
- clasificación explícita `existing_certified_flow`, fuera de la prioridad free-first;
- metadata de decisión en auditoría;
- feature flag y rollback inmediato.

### Fase B — Groq para texto de bajo riesgo

- adaptador `AIProvider`;
- benchmark de JSON/copy autorizado;
- rollout solo en staging;
- free tier como primario para tareas nuevas, nunca para sustituir el copy actual;
- OpenRouter free fijado como alternativa gratuita opcional;
- OpenAI como fallback técnico solo con gasto autorizado;
- límites de cuota, circuit breaker y `paid_fallback_allowed=false` por defecto.

### Fase C — Cloudflare/FLUX free-first

- ejecutar el plan `ai-image-generation-plan.md`;
- validar `@cf/black-forest-labs/flux-2-klein-4b`, licencia y cuenta Workers Free;
- imagen base sin logos/copy;
- piloto en un formato social;
- hard cap de Neurons, límites de regeneración y no activar para todos los briefs.

### Fase D — Gemini free en laboratorio

- solo datos sintéticos o públicos;
- leer y registrar la cuota real del proyecto en AI Studio;
- adaptador visual compatible con el schema actual;
- comparación ciega contra Anthropic como benchmark, sin reemplazarlo;
- no habilitar producción ni fallback automático.

### Fase E — Premium compare

- opt-in por rol;
- dos candidatos inicialmente;
- juez estructurado;
- tablero de costos y resultados;
- revisión humana obligatoria.

### Diferidos

- cualquier uso del router aleatorio `openrouter/free` en producción;
- Gemini pagado, retirado de esta propuesta;
- Ollama hasta contar con infraestructura GPU externa y un caso financiero favorable.

## 12. Decisiones pendientes para Axel

Antes de construir, Axel debe confirmar explícitamente:

1. **Primer proveedor nuevo:** confirmar Groq free para texto rápido de tareas nuevas; recomendación,
   comenzar por interpretación de brief o mejora de prompt, no por el copy actual.
2. **Proveedor de imagen para el piloto:** confirmar Cloudflare Workers AI con FLUX.2 `[klein]` 4B
   en Workers Free; OpenAI Images queda como alternativa premium, no como primario.
3. **Presupuesto:** monto mensual y máximos por tarea, imagen y pieza aceptada.
4. **Fallback pagado:** qué tareas nuevas pueden activar OpenAI/Anthropic después de agotar las
   opciones gratis. Recomendación inicial: ninguna sin `paid_fallback_allowed=true` explícito.
5. **Fallback creativo:** conservador —solo errores técnicos— o más agresivo —también calidad
   insuficiente—. Recomendación inicial: conservador.
6. **Calidad por tarea:** qué operaciones pueden usar modelos `economy` y cuáles exigen `premium`;
   la revisión final antes de cliente es el primer caso premium propuesto.
7. **Privacidad:** ZDR obligatorio, proveedores/regiones permitidos y si el free tier de cualquier
   candidato queda prohibido con datos reales.
8. **Gemini free:** confirmar que queda limitado a pruebas sintéticas/públicas o retirarlo por
   completo del shortlist.
9. **Modo premium:** qué roles/campañas pueden pedir comparación multi-motor y cuántos candidatos.
10. **Juez:** si puede recomendar un ganador o solo presentar un score a revisión humana.
11. **Regeneraciones:** máximo automático por pieza; recomendación inicial, una.
12. **OpenRouter:** si se desea como contingencia gratuita de bajo volumen o se evita para mantener
    trazabilidad directa con cada proveedor.
13. **Ollama:** confirmar que queda fuera de Railway; solo reconsiderarlo con GPU externa.
14. **Umbrales de benchmark:** tasa mínima de schema válido, precisión visual, aceptación humana,
    latencia y costo para promover un candidato a producción.

## 13. Criterio de terminado del futuro AI Router

La implementación futura no se considera terminada solo porque pueda llamar dos APIs. Debe
demostrar que:

- los flujos actuales producen el mismo resultado con el router habilitado;
- cada intento y fallback queda auditado con proveedor/modelo real;
- ningún proveedor recibe datos fuera de `authorized_context`;
- un fallback no degrada privacidad, permisos, marca ni modo de generación;
- los límites de gasto detienen nuevas llamadas de forma predecible;
- las reglas deterministas son idénticas para todos los proveedores;
- el sistema puede desactivar un proveedor sin reconstruir el flujo;
- las decisiones de routing son explicables y reproducibles;
- existe rollback al proveedor actual;
- staging pasa el benchmark aprobado antes de cualquier activación en producción.

## 14. Fuera de alcance de este documento

- instalar SDKs o dependencias;
- crear adaptadores, modelos, migraciones, endpoints o variables;
- activar Groq, Gemini, OpenRouter, Cloudflare, Ollama u otro proveedor;
- cambiar OpenAI o Anthropic actuales;
- implementar generación de imágenes;
- modificar `backend/security/`, SSO, roles o autenticación;
- intervenir en la certificación end-to-end;
- elegir presupuesto, proveedor o modelo definitivo sin aprobación de Axel.
