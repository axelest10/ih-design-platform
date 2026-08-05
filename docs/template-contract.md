# Contrato de plantillas

Las plantillas viven en `frontend/templates/designs/` y deben ser neutrales respecto a productos y promociones. El renderizador futuro recibirá `render_data` desde una `DesignVersion` y solo podrá inyectar campos explícitos:

- `logo`: referencia a un `OfficialAsset` aprobado; nunca una imagen generada.
- `headline` y `body`: copy revisado, con longitud y contraste validados.
- `price`, `date`, `location`, `contact` y `cta`: valores provenientes de catálogo/campaña/sede.

Cada formato debe conservar sus dimensiones oficiales y una zona segura consistente. No se debe escribir información comercial directamente dentro de un SVG versionado.
