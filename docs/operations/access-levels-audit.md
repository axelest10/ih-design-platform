# Auditoría de niveles de acceso

Fecha de auditoría: 2026-08-09. Alcance: documentación del comportamiento actual; **no se
modificaron permisos ni asignaciones de rol**.

Fuentes revisadas:

- `backend/security/permissions.py`
- `backend/security/management/commands/sync_corporate_roles.py`
- `backend/api_urls.py` y todos los `backend/*/views.py`
- `backend/config/settings.py`
- `IH_Design_Platform_Scoping_Document_v4.docx`, secciones 11 y 12

## Cómo se aplican hoy los permisos

1. `CorporateDomainPermission` es el permiso global de DRF cuando
   `CORPORATE_AUTH_REQUIRED=True`: exige sesión y un dominio de correo autorizado.
2. `RoleAwareViewSet` añade `RolePermission` únicamente cuando la acción actual aparece en
   `role_rules`.
3. Si una acción no aparece en `role_rules`, cualquier usuario corporativo autenticado puede
   ejecutarla. `is_staff` e `is_superuser` omiten las restricciones por rol.
4. Algunos querysets agregan límites por propietario. Esto reduce qué objetos ve cada usuario,
   pero no equivale a una autorización por rol.
5. Las excepciones `AllowAny` se enumeran explícitamente más adelante.

## Roles actuales

Las descripciones son las definidas en
`backend/security/management/commands/sync_corporate_roles.py::ROLE_DESCRIPTIONS`.

| Rol | Descripción actual |
| --- | --- |
| `platform_admin` | Administra configuración y permisos de la plataforma. |
| `marketing` | Gestiona catálogo comercial, campañas, briefs y diseños. |
| `designer` | Crea briefs, diseños, previews y validaciones. |
| `reviewer` | Ejecuta validaciones y aprueba o rechaza diseños. |
| `viewer` | Consulta información autorizada sin editarla. |

## Matriz actual de acciones con `role_rules`

La tabla refleja el código existente. No representa una ratificación de negocio por Axel.

| App | Viewset | Acción | Roles permitidos hoy |
| --- | --- | --- | --- |
| assets | `OfficialAssetViewSet` | `create` | `platform_admin`, `marketing` |
| assets | `OfficialAssetViewSet` | `update`, `partial_update` | `platform_admin`, `marketing` |
| assets | `OfficialAssetViewSet` | `destroy` | `platform_admin` |
| assets | `UploadedLogoViewSet` | `create` | `platform_admin`, `marketing`, `designer` |
| assets | `UploadedLogoViewSet` | `update`, `partial_update` | `platform_admin` |
| assets | `UploadedLogoViewSet` | `destroy` | `platform_admin` |
| assets | `ArtworkReferenceViewSet` | `create` | `platform_admin`, `marketing`, `designer` |
| assets | `ArtworkReferenceViewSet` | `update`, `partial_update` | `platform_admin`, `marketing`, `reviewer` |
| assets | `ArtworkReferenceViewSet` | `destroy` | `platform_admin` |
| assets | `ArtworkReferenceViewSet` | `approve`, `reject` | `platform_admin`, `reviewer` |
| branding | `BrandGuidelineViewSet` | `create` | `platform_admin`, `marketing` |
| branding | `BrandGuidelineViewSet` | `update`, `partial_update` | `platform_admin`, `marketing` |
| branding | `BrandGuidelineViewSet` | `destroy` | `platform_admin` |
| briefs | `DesignBriefViewSet` | `create` | `platform_admin`, `marketing`, `designer` |
| briefs | `DesignBriefViewSet` | `update`, `partial_update` | `platform_admin`, `marketing`, `designer` |
| briefs | `DesignBriefViewSet` | `destroy` | `platform_admin`, `marketing` |
| briefs | `BriefReferenceUploadViewSet` | `create`, `destroy` | `platform_admin`, `marketing`, `designer` |
| campaigns | `CampaignViewSet` | `create` | `platform_admin`, `marketing` |
| campaigns | `CampaignViewSet` | `update`, `partial_update` | `platform_admin`, `marketing` |
| campaigns | `CampaignViewSet` | `destroy` | `platform_admin` |
| catalog | `ProductViewSet` | `create` | `platform_admin`, `marketing` |
| catalog | `ProductViewSet` | `update`, `partial_update` | `platform_admin`, `marketing` |
| catalog | `ProductViewSet` | `destroy` | `platform_admin` |
| catalog | `BranchViewSet` | `create` | `platform_admin`, `marketing` |
| catalog | `BranchViewSet` | `update`, `partial_update` | `platform_admin`, `marketing` |
| catalog | `BranchViewSet` | `destroy` | `platform_admin` |
| designs | `DesignViewSet` | `create`, `update`, `partial_update` | `platform_admin`, `marketing`, `designer` |
| designs | `DesignViewSet` | `destroy` | `platform_admin` |
| designs | `DesignViewSet` | `preview` | `platform_admin`, `marketing`, `designer` |
| designs | `DesignViewSet` | `claude_review` | `platform_admin`, `marketing`, `designer` |
| designs | `DesignViewSet` | `review` | `platform_admin`, `reviewer` |
| materials | `MaterialBundleViewSet` | `create`, `update`, `partial_update` | `platform_admin`, `marketing`, `designer` |
| materials | `MaterialBundleViewSet` | `destroy` | `platform_admin` |
| materials | `MaterialBundleViewSet` | `generate` | `platform_admin`, `marketing`, `designer` |
| validations | `ValidationRunViewSet` | `create` | `platform_admin`, `designer`, `reviewer` |
| validations | `ValidationRunViewSet` | `update`, `partial_update` | `platform_admin`, `reviewer` |
| validations | `ValidationRunViewSet` | `destroy` | `platform_admin` |

No se encontraron otros viewsets con `role_rules` fuera de `assets`, `branding`, `briefs`,
`campaigns`, `catalog`, `designs`, `materials` y `validations`.

## Acciones y endpoints sin distinción por rol

### Requieren sesión corporativa, pero no un rol específico

| Superficie | Acceso efectivo actual | Observación |
| --- | --- | --- |
| `list` y `retrieve` de los 12 viewsets de la matriz anterior | Cualquier usuario corporativo | Ninguno declara reglas para lectura. |
| `ArtworkReferenceViewSet.knowledge` | Cualquier usuario corporativo | Acción GET sin entrada en `role_rules`; expone la base de conocimiento visual. |
| `DesignBriefViewSet.options` | Cualquier usuario corporativo | Acción GET sin entrada en `role_rules`; alimenta países, productos y logos del brief. |
| `BriefReferenceUploadViewSet.update/partial_update` | Cualquier usuario corporativo sobre objetos visibles | Hallazgo relevante: son acciones mutables sin regla de rol. El queryset limita usuarios no administradores a sus propios uploads. |
| `MaterialTypeViewSet` | Cualquier usuario corporativo | No define `role_rules`, pero limita métodos a GET/HEAD/OPTIONS. |
| `MaterialTemplateViewSet` | Cualquier usuario corporativo | No define `role_rules`, pero limita métodos a GET/HEAD/OPTIONS. |
| `GET /api/v1/me/` | Cualquier usuario corporativo | Devuelve perfil, roles y capacidades derivadas. |

Límites por propietario existentes, independientes del rol:

- `UploadedLogoViewSet`, `DesignBriefViewSet`, `BriefReferenceUploadViewSet` y
  `MaterialBundleViewSet` filtran el queryset para usuarios no administradores.
- Los demás catálogos de lectura no aplican filtro regional o por propietario desde el viewset.

### Públicos, sin sesión

| Endpoint | Motivo/comportamiento actual |
| --- | --- |
| `GET /api/v1/health/` | Liveness probe de Django, fuera de DRF. |
| `POST /api/v1/auth/site-access/` | Valida la contraseña compartida, limita por IP y está marcado `AllowAny`. |
| `GET /api/v1/branding/tokens/` | Catálogo público no sensible de tokens. |
| `GET /api/v1/branding/logos/` | Catálogo público de logos aprobados. |
| `GET /api/v1/branding/validate-color/` | Validación pública contra colores autorizados. |

## Brechas conocidas frente al estándar de referencia

El scoping v4, sección 11, registra textualmente:

> “Ausente frente al estándar de IH Connect: flujo de invitación explícito, reseteo de
> contraseña, verificación de email, límite de intentos de login (rate limiting), bloqueo tras
> fallos repetidos, 2FA para roles administrativos. Ninguno está confirmado en el código
> revisado.”

El resumen de seguridad del mismo documento añade:

> “Existe el gate de dominio corporativo. Faltan, respecto al estándar de IH Connect: cabeceras
> de seguridad (Helmet o equivalente Django), rate limiting en endpoints sensibles, 2FA para
> roles administrativos, CORS estricto documentado — ninguno confirmado en el repo actual.”

Evaluación contra el código actual después de adoptar el acceso compartido sin identidad:

| Brecha de referencia | ¿Aplica al acceso compartido? | Estado observado |
| --- | --- | --- |
| Flujo de invitación explícito | No, por decisión de Axel | No existe identidad individual: quien conoce la contraseña compartida entra como el mismo usuario técnico. |
| Reseteo de contraseña | Sí, como rotación operativa | La contraseña se rota cambiando `SITE_ACCESS_PASSWORD` en el entorno; no hay autoservicio. |
| Verificación de email | No, por decisión de Axel | El acceso ya no depende de correo ni de un proveedor de entrega. |
| Rate limiting | Sí | `POST /api/v1/auth/site-access/` limita por IP; la tasa predeterminada es `10/hour`. |
| Bloqueo tras fallos repetidos | Parcialmente | El throttle bloquea temporalmente por IP, pero no existe bloqueo persistente ni por identidad. |
| 2FA para roles administrativos | Sí | No existe segundo factor; toda sesión compartida reúne los cinco roles. |
| Cabeceras de seguridad tipo Helmet/equivalente Django | Sí | Se configuraron cabeceras explícitas y una CSP estricta, verificadas mediante pruebas. |

## Preguntas abiertas para Axel

1. ¿Cómo se distribuirá y rotará operativamente `SITE_ACCESS_PASSWORD`?
2. ¿En qué momento será necesario recuperar identidad individual y roles diferenciados?
3. Si se recupera identidad, ¿debe `viewer` leer todos los catálogos y referencias LATAM o solo datos del país asociado a
   su cuenta?
4. ¿Se ratifica que `marketing` y `designer` puedan ejecutar `claude_review`, mientras
   `reviewer` queda reservado para la decisión humana `review`?
5. ¿Debe restringirse `BriefReferenceUploadViewSet.update/partial_update` a los mismos roles que
   `create/destroy`, o basta el filtro actual por propietario?
6. ¿Las lecturas `list/retrieve` de campañas, productos, sedes, validaciones y activos deben ser
   globales para cualquier usuario corporativo o deben limitarse por rol y país?
7. ¿Se requerirá 2FA cuando vuelva a existir identidad administrativa individual?

## Seguimiento de endurecimiento (2026-08-10)

Las brechas de rate limiting en el acceso y de cabeceras de seguridad se resolvieron
con controles explícitos y verificables:

- El endpoint de contraseña compartida limita por defecto a `10/hour` por IP. El valor se puede
  ajustar mediante `SITE_ACCESS_THROTTLE_RATE`.
- Las respuestas incluyen `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`,
  `Cross-Origin-Opener-Policy: same-origin` y `X-Frame-Options: DENY`.
- La CSP permite recursos del mismo origen, imágenes `data:` y el origen específico
  `https://cdn.jsdelivr.net` en `script-src` para el renderizador versionado de Markdown. Bloquea
  framing y no admite `unsafe-inline` ni `unsafe-eval`; `frame-ancestors` usa `'none'`.

Estos controles mitigan abuso básico y endurecen el navegador; no resuelven las preguntas
separadas sobre rotación del secreto, 2FA, segmentación por país o una futura recuperación de
identidad individual.
