# Feature Specification: Remediación post-auditoría web EcoGrow

**Feature Branch**: `001-auditoria-web`  
**Created**: 2026-05-26  
**Status**: Implemented (pendiente validación en producción HTTPS)  
**Input**: Auditoría total solicitada — SquirrelScan + revisión de código + alineación Spec Kit

## User Scenarios & Testing

### User Story 1 - Seguridad coherente en UI admin (Priority: P0)

Como administrador, quiero que el modo Admin solo se active si mi correo está en `ECOGROW_ADMIN_EMAILS`, para que usuarios normales no vean controles de administración.

**Independent Test**: Usuario no admin logueado ve `ui_mode=user` y no ve bloques `ui_mode == 'admin'`; admin puede alternar con `/modo/admin`.

**Acceptance Scenarios**:

1. **Given** usuario autenticado sin email admin, **When** carga `/cultivos`, **Then** no ve historial de ciclos reservado a admin.
2. **Given** usuario con email en `ADMIN_EMAILS`, **When** visita `/modo/admin`, **Then** `session['ui_mode']` es `admin` y ve controles admin.

---

### User Story 2 - SEO y descubrimiento en producción (Priority: P1)

Como visitante o buscador, quiero metadatos correctos, sitemap y política de privacidad, para confiar en el sitio y que sea indexable.

**Independent Test**: SquirrelScan en URL HTTPS de producción mejora Core SEO y Crawlability; existen `/robots.txt`, `/sitemap.xml`, `/privacidad`.

**Acceptance Scenarios**:

1. **Given** despliegue en HTTPS, **When** se audita con Squirrel, **Then** no falla `security/https` en páginas públicas.
2. **Given** cualquier página pública, **When** se inspecciona el `<head>`, **Then** tiene título y descripción únicos (≥30 y ≥120 caracteres respectivamente).

---

### User Story 3 - Rendimiento percibido en landing (Priority: P2)

Como visitante en la home, quiero que la imagen principal no provoque saltos de layout y cargue rápido.

**Independent Test**: `hero.png` tiene width/height; Lighthouse/Squirrel no reporta CLS en `/`.

**Acceptance Scenarios**:

1. **Given** la página `/`, **When** carga el hero, **Then** la imagen tiene dimensiones explícitas o aspect-ratio reservado.

---

## Requirements

### Functional Requirements

- **FR-001**: El sistema DEBE calcular `ui_mode` desde sesión solo para usuarios admin verificados por email.
- **FR-002**: El sistema DEBE servir `robots.txt` y `sitemap.xml` con rutas públicas indexables.
- **FR-003**: El sistema DEBE exponer una página de política de privacidad enlazada desde el layout base.
- **FR-004**: Cada plantilla pública DEBE poder sobrescribir `title` y `meta description` sin duplicar el texto genérico de `base.html`.
- **FR-005**: Los activos estáticos DEBEN enviar cabeceras de caché en producción.

### Non-Functional Requirements

- **NFR-001**: Tras cambios P0, la suite `tests/test_app.py` DEBE seguir en verde (15/15).
- **NFR-002**: Re-auditoría Squirrel en producción DEBE alcanzar ≥75 en Core SEO y Crawlability (objetivo intermedio).

## Success Criteria

- [x] Bug `ui_mode` corregido y test añadido para usuario no admin
- [x] `robots.txt`, `sitemap.xml`, favicon, OG básicos desplegados
- [ ] Informe Squirrel en producción documentado en `docs/auditoria/` (ver `CHECKLIST-PRODUCCION.md`)
- [x] Constitution EcoGrow en `.specify/memory/constitution.md`

## Assumptions

- La app se despliega en Render con HTTPS y variables de `render.yaml`.
- La auditoría local HTTP seguirá marcando fallos de HTTPS hasta auditar producción.

## Out of Scope

- Refactor completo de `Conexión/conexion.py`
- Tests E2E Playwright (skill `webapp-testing` disponible para fase posterior)
