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
- En Staging, OIDC valida el issuer del Hub, callback exacto, PKCE S256, estado, nonce, audience,
  expiración, JWKS y firma RS256 antes de crear una sesión Django.
- `HubIdentity` usa `sub` como identidad permanente; el email solo participa en el primer enlace
  único. Los nuevos usuarios reciben exclusivamente `viewer`.
- Los roles permanecen locales y los eventos de identidad son append-only sin tokens ni secretos.

## Pendiente / no confirmado

Quedan fuera de v1 el logout global, la revocación push y 2FA administrativo adicional. La
revocación de una cuenta del Hub queda acotada por la sesión Design de 900 segundos. También
siguen pendientes un proceso general de secret scanning y CORS para un frontend separado. No se
agregan aquí reglas que no estén implementadas.
