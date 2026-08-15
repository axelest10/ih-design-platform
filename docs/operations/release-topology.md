# Topología de releases y aislamiento de entornos

Esta aplicación usa dos historiales de release independientes dentro del mismo proyecto de
Railway. Compartir el identificador lógico de un servicio entre entornos no autoriza compartir
datos, volúmenes, credenciales ni sesiones.

## Flujo autorizado

```text
feature branch
  -> Pull Request / CI
  -> Staging
  -> UAT
  -> merge a main
  -> aprobación explícita de release
  -> promoción manual del SHA exacto de main a Production
```

Un `push` o `merge` nunca debe desplegar Production por sí solo.

## Mapeo actual

| Entorno | Railway environment | Fuente | Trigger | Wait for CI | Dominio |
| --- | --- | --- | --- | --- | --- |
| Staging | `74f3cbd5-b558-4948-9dc3-e0849f642891` | `axelest10/ih-design-platform`, temporalmente `codex/hub-sso` | automático, solo Staging | activado | `mydesign-staging.ihlatam.com` |
| Production | `bd91b87f-8e0e-4001-a700-5da5e1df4864` | `axelest10/ih-design-platform`; la promoción manual toma la rama por defecto `main` | ninguno; autodeploy desactivado | no aplica al no existir trigger | `mydesign.ihlatam.com` |

Cuando el PR de SSO se fusione, Staging debe volver de `codex/hub-sso` a `main`. No se debe
conservar un entorno permanente ligado a la rama de feature.

## CI y promoción exacta a Production

El job obligatorio de aplicación es `CI / test`. Antes de fusionar, debe finalizar en verde sobre
el SHA candidato. La protección de `main` debe exigir Pull Request y ese check desde la
configuración administrativa de GitHub.

Production se publica solo por una persona responsable del release desde Railway con **Deploy
Latest Commit**, después de verificar que:

1. `main` apunta exactamente al SHA aprobado y no avanzó desde la aprobación;
2. `CI / test` está en verde para ese mismo SHA;
3. Staging y el UAT corresponden al mismo árbol de código;
4. las variables/migraciones de Production fueron revisadas;
5. el cambio tiene rollback identificado.

Railway toma en esa operación el último commit de la rama por defecto de GitHub. Si `main` avanzó,
se cancela la promoción; no se despliega un SHA distinto por conveniencia. Después del deploy se
deben registrar `deployment ID`, `commitHash`, salud, migraciones y logs. Nunca se habilita un
trigger de Production como atajo.

## Aislamiento obligatorio

- PostgreSQL: cada entorno tiene su propia instancia, dirección privada, identificador de cluster
  y estado. `DATABASE_URL` debe resolver dentro del mismo Railway environment.
- Redis: cada entorno tiene su propia instancia, volumen y `run_id`. `REDIS_URL` nunca se copia
  entre entornos.
- Objetos: Staging usa el bucket Railway `design-staging-media-cyej8u`
  (`d59a7998-f9a3-4f0f-ba7c-4e235e287c8f`) con credenciales exclusivas. Production conserva su
  bucket R2 existente; su nombre histórico contiene `staging`, pero desde esta corrección es un
  recurso exclusivo de Production y no debe volver a enlazarse desde Staging. Renombrarlo o migrar
  datos requiere un cambio de Production separado.
- Sesiones: las cookies son host-only y cada entorno usa un `DJANGO_SECRET_KEY` distinto. No se
  configura `SESSION_COOKIE_DOMAIN` compartido.
- Proveedores de IA: sus credenciales son por entorno. Una variable ausente significa integración
  deshabilitada; nunca se copia una clave de Production a Staging.
- OIDC: Staging usa issuer, client ID, secreto y callback exclusivos. Production mantiene
  `HUB_OIDC_ENABLED=0` (o ausente), no tiene credenciales OIDC y conserva el login local hasta una
  aprobación de cutover independiente.

## Correo

El código nuevo usa exclusivamente Postmark. Staging empieza en `EMAIL_DELIVERY_MODE=disabled` y,
cuando el propietario instale directamente el token del servidor **IH Design — Staging**, solo
puede pasar a `allowlist` con destinatarios de prueba aprobados. Una lista vacía falla cerrada y
`live` se rechaza fuera de Production. El remitente es
`IH Design <mydesign@ihlatam.com>` desde el dominio padre ya verificado `ihlatam.com`; las
credenciales nunca se comparten con Hub.

Production continúa ejecutando el SHA anterior dependiente de Resend hasta una migración manual
separada. No se elimina `RESEND_API_KEY` mientras ese contenedor siga activo. La secuencia segura
es preparar variables del servidor **IH Design — Production**, promover un SHA provider-only
revisado con SSO apagado, verificar salud/login/recuperación controlada y solo entonces retirar
las variables Resend y revocar la clave expuesta en su workspace real.

## Variables y cambios pendientes

Los cambios de variables de Production se guardan con `--skip-deploys` cuando no deben reiniciar el
servicio. En particular, la corrección a `DJANGO_ENV=production` se aplica en el siguiente release
manual aprobado; no se genera un deploy solo para materializarla. Antes de promover se revisa el
diff de variables y se confirma nuevamente que OIDC de Production sigue apagado.

## Rollback

- Staging: desactivar `HUB_OIDC_ENABLED`, desplegar de nuevo el último SHA conocido como bueno y
  verificar login local, salud y logs. No borrar `HubIdentity` ni revertir migraciones aditivas.
- Production: elegir el deployment anterior cuyo `commitHash` sea el SHA de rollback aprobado y
  usar la acción Railway Rollback. Confirmar dominio, salud, revisión y logs; el autodeploy debe
  permanecer apagado.
- Datos: cualquier rollback destructivo de esquema o restauración de PostgreSQL, Redis u objetos
  exige un plan y autorización separados. No se improvisa desde el flujo de código.

## Break-glass

Solo la persona responsable del release puede iniciar Production. Debe registrar motivo, SHA,
deployment ID y evidencia posterior. Una urgencia no autoriza reactivar autodeploy, seguir una
rama de feature, omitir CI, compartir recursos de Staging ni habilitar SSO. Si Railway no permite
promover sin cambiar el SHA esperado, se detiene el release.
