# Biblioteca de artes de referencia — IH LATAM

Esta biblioteca conserva artes históricos y actuales encontrados en la carpeta
compartida de Drive organizada por país. Sirve como base de consulta e inspiración
para nuevas piezas; no convierte automáticamente ningún arte en una regla oficial.

## Estructura

```text
artwork-references/
├── manifest.yaml       Inventario generado con 454 referencias y su procedencia
├── README.md
├── chile/              Imágenes copiadas desde Drive
├── colombia/
├── ielts-latam/
├── mexico/
└── peru/
```

La capa JSON para consumo del backend y de agentes creativos está en
`brand/knowledge/artwork-reference-knowledge.json`. La manifest conserva el registro
operativo; el JSON agrega metadata técnica, hashes, proporciones, paletas observadas y
facetas de selección sin inventar reglas de marca.

Las imágenes se versionan localmente. Los 140 videos se mantienen como referencias
de Drive (`source_url`) para evitar incorporar binarios grandes sin una política de
almacenamiento aprobada.

## Estado y uso

- Todas las entradas tienen `reference_type: inspiration` y `approval_status: pending`.
- Antes de reutilizar, adaptar o publicar una pieza se debe confirmar el país, la
  marca/producto, los derechos de uso y la revisión del responsable de marca.
- El backend puede sincronizar el inventario con:

  `python manage.py sync_artwork_references`

- El comando es idempotente y conserva el estado de aprobación existente; solo
  actualiza metadata y procedencia.

El manifest es generado por `brand/scripts/build_artwork_catalog.py` a partir del
inventario de Drive. No editar entradas individuales a mano: actualizar la fuente y
regenerar el catálogo.
