# EcoGrow Constitution

## Core Principles

### I. Seguridad primero (IoT y usuarios)

Toda entrada externa (formularios, API ESP32, chat IA) debe validarse. Las APIs de dispositivos usan token dedicado; los formularios web usan CSRF. Los permisos de administración se basan en lista explícita de correos (`ECOGROW_ADMIN_EMAILS`), no en flags de sesión manipulables.

### II. Especificación antes de código grande

Funcionalidades nuevas o refactors amplios siguen Spec Kit: especificación (`specs/`), plan, tareas, implementación. La auditoría y remediación web viven en `specs/001-auditoria-web/`.

### III. Tests como red de seguridad

Cambios en auth, CSRF y permisos deben mantener `tests/test_app.py` en verde. Añadir tests al corregir bugs de seguridad (ej. `ui_mode`).

### IV. Capas claras

Blueprints → services/models → `Conexión` (datos). No duplicar lógica de negocio en plantillas. Preferir extender servicios existentes antes de nuevos accesos SQL en vistas.

### V. UX hidropónica honesta

La UI debe reflejar el rol real del usuario (agricultor vs admin). No mostrar controles que el backend rechazaría. Telemetría sin datos se muestra como “Sin dato”, no como valores inventados.

### VI. Dominio agronómico por fase

Los rangos de control (pH, EC, riego) deben derivar de la **fase fenológica activa** del ciclo en torre (`domain/hidroponia_torre.py`), no de valores genéricos inadecuados para hidroponía. Documentar decisiones en `docs/hidroponia/`.

## Restricciones técnicas

- Python 3 + Flask; MySQL como fuente de verdad en producción.
- Variables sensibles solo por entorno; nunca en el repositorio.
- Despliegue Render: `SESSION_COOKIE_SECURE=true`, `SECRET_KEY` y `ECOGROW_SENSOR_API_TOKEN` fijos.

## Calidad web pública

- Páginas públicas: SEO básico (título, descripción, sitemap, robots, privacidad).
- Accesibilidad: jerarquía de encabezados, textos alternativos en imágenes.
- Re-auditar con SquirrelScan tras cambios relevantes en `templates/` o rutas públicas.

## Governance

Esta constitución guía decisiones de diseño. En conflicto con código legacy, abrir spec de remediación antes de parches ad hoc. Amendments: actualizar este archivo y la fecha abajo.

**Version**: 1.0.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26
