# Operaciones

- [`deployment.md`](deployment.md): preparación de staging, variables requeridas y comparativo de
  proveedores.
- [`../hub-sso-exec-plan.md`](../hub-sso-exec-plan.md): contrato, secuencia, pruebas, rollback y
  plan futuro de migración para SSO con IH LATAM Hub.
- [`approval-flow.md`](approval-flow.md): recomendación para retirar gradualmente el endpoint
  legacy de aprobación.

El entorno de Staging de Railway existe y su salud base está documentada en `deployment.md`.
Todavía falta documentar y ensayar un runbook general de incidentes/backups; el SSO sí incluye
un rollback acotado por feature flag que conserva enlaces y auditoría.
