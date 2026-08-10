# Frontend y templates de renderizado

El frontend visual completo se reserva para la aplicación de solicitudes guiadas y revisión
visual. Los templates sociales reutilizables ya están versionados en:

- `index.html` — Home responsive del workspace LATAM.
- `panel.html` — brief guiado, carga de logos y paneles según rol.
- `school-kit.html` — creación, edición, generación y registro de revisión por pieza para la
  paquetería de colegios.
- `marketing-materials.html` — biblioteca pública descargable por marca, país y categoría.
- `styles/home.css` y `scripts/home.js` — sistema visual e interacción básica de la Home.
- `styles/panel.css` y `scripts/panel.js` — formulario de 20 preguntas conectado a la API.

- `templates/designs/square-v1.html`
- `templates/designs/square-v1.svg`
- `templates/designs/story-v1.html`
- `templates/designs/story-v1.svg`
- `templates/designs/portrait-v1.html`
- `templates/designs/portrait-v1.svg`
- `templates/manifest.yaml`

Ambas salidas usan el mismo contrato de datos, tamaño 1080 × 1080, tokens de `brand/` y un logo
aprobado del catálogo LATAM. Aptos se conserva como fallback documental; el repositorio no
redistribuye sus archivos `.ttf`.

## Flujo de preview y revisión

1. Crear un `Design` asociado a un `DesignBrief`.
2. `POST /api/v1/designs/{id}/preview/` con `headline`, `body`, `cta`, `logo_name` y tokens de
   color opcionales.
3. El backend genera HTML y SVG, guarda una `DesignVersion` y, para briefs de producto,
   cambia el diseño a `self_review` dentro del modo de primeras 50 pruebas.
4. `POST /api/v1/designs/{id}/claude-review/` guarda el resultado `pass|needs_changes` sin
   aprobar humanamente la pieza. La aprobación formal queda para después de las 50 pruebas.

La vista `school-kit.html` crea un paquete, permite seleccionar varios productos y genera tres
entregables sociales por producto, más carta, anuncio y flyer una sola vez por paquete. Los colores de producto
con pilar documentado se resuelven desde `brand/product-colors/authorized-colors.yaml`; un producto
sin color confirmado queda señalado para revisión, no recibe una paleta inventada.

El renderizador rechaza templates desconocidos, logos no aprobados, colores fuera de tokens, texto
crítico vacío o demasiado largo, desbordamiento de ancho, colisiones, salida de zona segura y
contraste insuficiente. El endpoint todavía está abierto para integración local; la autenticación
corporativa y los roles ya tienen gate de backend, mientras que los comentarios persistidos quedan
para la siguiente fase.
