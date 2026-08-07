# Colores autorizados por producto — International House México

`authorized-colors.yaml` es la fuente única de verdad para qué color(es) corresponden a cada
pilar/producto de negocio de IH México. Confirmado por el cliente el 2026-08-05 con base en el
documento `IH_BRANDING_MARCA.docx` (tabla "Sistema de Colores por Pilar"), idéntico a
`IH_Mexico_Sistema_Diseno_Web.docx`.

## Pilares y color principal

| Pilar | Color principal | Token |
| --- | --- | --- |
| Inglés General | #B7DB6E | `youth` |
| Cambridge | #923472 | `technology` |
| University Programmes | #3B44B5 | `knowledge` |
| Inglés para Empresas | #28AE62 | `green` |
| IELTS | #E31736 | `ielts_red` (extensión MX) |
| Spanish Courses | #F4AB63 | `light` |

Cada pilar tiene además un color secundario, un color de fondo (tinte claro) y una
configuración de CTA — ver `authorized-colors.yaml` para el detalle completo con
justificación de marca de cada elección.

## Reglas de uso

1. No mezclar el color principal de un pilar con el de otro pilar en la misma pieza.
2. El color de fondo es siempre un tinte claro del pilar — no sustituirlo por blanco puro.
3. El texto sobre CTA de color es blanco, salvo excepción documentada.
4. El rojo IELTS es una extensión exclusiva de México, no forma parte de la paleta de 8
   colores del manual global y no debe usarse fuera del pilar IELTS.

## Validación

`backend/branding/services/color_validation.py` valida que cualquier color usado en un brief o
diseño para un pilar específico corresponda a uno de los valores autorizados en este archivo
(o a la paleta institucional general de `brand/tokens/colors.yaml`). Ver
`tests/test_branding_tokens.py`.

## Fuentes descartadas para este archivo

Ver `authorized-colors.yaml -> alternate_sources_not_used` para el detalle de por qué
`IH_Sistema_Colores_v2.docx` y `Color por producto.pdf` no se usaron como fuente de este
archivo (documentos con valores divergentes, superados por la confirmación del cliente).
