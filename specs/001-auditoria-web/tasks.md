# Tasks: 001-auditoria-web

**Input**: [spec.md](./spec.md) + [plan.md](./plan.md)

## Phase 1 — P0 Seguridad UI

- [x] T001 Corregir `ui_mode` en `blueprints/shared.py` usando `is_admin_user()` y `session.get("ui_mode")`
- [x] T002 Añadir test: usuario no admin con sesión `ui_mode=admin` no ve comportamiento admin en contexto (opcional: integración plantilla)
- [x] T003 Verificar plantillas `cultivos/lista.html`, `sensores.html`, `ciclo_form.html` usan `is_admin_mode` o `ui_mode` corregido
- [x] T004 Documentar en README variable `ECOGROW_ADMIN_EMAILS`

## Phase 2 — P1 SEO y legal

- [x] T005 Ruta `GET /robots.txt` (Allow /, Disallow rutas privadas si aplica)
- [x] T006 Ruta `GET /sitemap.xml` con URLs públicas
- [x] T007 Plantilla `privacidad.html` + ruta + enlace footer
- [x] T008 Bloques `{% block title %}` y `{% block meta_description %}` en páginas públicas
- [x] T009 Favicon + `og:title`, `og:description`, `og:image` en `base.html`
- [x] T010 Corregir jerarquía H1→H2→H3 en about, contactos, login, registro, demo

## Phase 3 — P2 Rendimiento

- [x] T011 Atributos width/height en hero + `fetchpriority="high"` / preload
- [x] T012 `preconnect` a `cdn.jsdelivr.net`
- [x] T013 Cache-Control para `/static/*` (Flask `send_file` max_age o WhiteNoise)

## Phase 4 — Validación

- [x] T014 Ejecutar tests unitarios (14/14)
- [x] T015 Squirrel audit local (`scripts/audit-local.sh` + reportes en `docs/auditoria/`)
- [ ] T016 Squirrel audit producción HTTPS (`docs/auditoria/CHECKLIST-PRODUCCION.md`)

## Phase 5 — Spec Kit (proceso)

- [x] T017 Constitution EcoGrow en `.specify/memory/constitution.md`
- [x] T018 Criterios de éxito actualizados en `spec.md` (pendiente solo T016 producción)

## Dependencies

```text
T001 → T002, T003
T005, T006 → T016
T008, T009 → T016 (SEO)
```

## Parallel opportunities

- T005–T007 pueden hacerse en paralelo (archivos distintos)
- T011–T013 independientes de SEO legal
