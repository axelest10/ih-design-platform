# Seguridad

La documentación operativa de acceso corporativo está en
[`docs/security.md`](../security.md). Este índice separa la ubicación futura de la documentación
sin duplicar reglas.

## Controles confirmados

- `CorporateDomainPermission` exige sesión y dominio autorizado cuando
  `DJANGO_REQUIRE_CORPORATE_AUTH=1`.
- La allowlist actual es `ihmexico.com`, `ihbogota.com`, `ihsantiago.cl` e `ihlima.com`.
- Los roles se modelan con grupos Django: `platform_admin`, `marketing`, `designer`, `reviewer` y
  `viewer`.
- El backend aplica permisos por acción mediante `RoleAwareViewSet`.
- El modo sin autenticación está documentado únicamente para desarrollo local.

## Pendiente / no confirmado

El repositorio no confirma todavía un proveedor SSO/OIDC/SAML, 2FA administrativo, rate limiting,
secret scanning, CORS para un frontend separado ni un audit log formal. No se agregan aquí reglas que
no estén implementadas.
