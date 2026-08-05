# Decisiones técnicas

## 2026-08-04 — Django modular como núcleo

Se elige Django + Django REST Framework para acelerar el MVP, mantener un modelo relacional explícito y exponer una API consumible por un frontend futuro.

## 2026-08-04 — Datos críticos fuera de la IA

Precios, fechas, promociones, logos, sedes, teléfonos y CTA se modelan como datos/activos autorizados y se reservan para la composición controlada. La IA recibe contexto permitido, pero no es fuente de verdad comercial.

## 2026-08-04 — SQLite local, PostgreSQL preparado

El entorno local y las pruebas usan SQLite por defecto para no requerir servicios externos. PostgreSQL se activa mediante `DB_ENGINE=postgresql` y es la configuración recomendada para staging/producción.

## 2026-08-04 — Interfaz de proveedor IA

`AIProvider` define el contrato interno. `OpenAIProvider` es el único adaptador inicial; la aplicación no importa directamente un SDK de otro proveedor.
