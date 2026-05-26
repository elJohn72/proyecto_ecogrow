# Implementation Plan: 001-auditoria-web

**Branch**: `001-auditoria-web` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

## Summary

Corregir el bug de permisos en UI (`ui_mode`), luego mejorar SEO/crawlability y rendimiento de la capa pública Flask, validando con SquirrelScan en producción.

## Technical Context

**Language/Version**: Python 3.12, Flask 3.1  
**Primary Dependencies**: Flask-Login, mysql-connector-python, Bootstrap 5 (CDN), fpdf2, google-generativeai  
**Storage**: MySQL/MariaDB  
**Testing**: `python3 -m unittest discover -s tests`  
**Target Platform**: Render (gunicorn), desarrollo local Flask  
**Project Type**: Monolito web Flask + Jinja2  

## Architecture Decisions

| Decisión | Elección | Razón |
|----------|----------|-------|
| Sitemap/robots | Blueprint `main` o `static` + rutas dedicadas | Sin dependencias extra |
| Meta por página | Bloques Jinja `{% block meta_description %}` | Evita duplicación en `base.html` |
| Headers seguridad | `@app.after_request` en `app.py` o proxy Render | CSP gradual para no romper CDN |
| ui_mode | `is_admin_mode()` en context processor | Una fuente de verdad |

## File Touch List (planned)

| Archivo | Cambio |
|---------|--------|
| `blueprints/shared.py` | Fix `ui_mode`, opcional `can_manage` documentado |
| `blueprints/main.py` | Rutas `robots.txt`, `sitemap.xml`, `privacidad` |
| `templates/base.html` | Favicon, OG defaults, footer legal, bloques meta |
| `templates/index.html` | Hero width/height, H2 en jerarquía |
| `tests/test_app.py` | Test `ui_mode` para usuario regular |
| `static/favicon.ico` | Nuevo asset |
| `docs/auditoria/` | Reportes post-fix |

## Validation Plan

1. `python3 -m unittest discover -s tests -v`
2. `squirrel audit http://127.0.0.1:5050 -C quick --format llm` (smoke)
3. `squirrel audit https://<render-url> -C surface --format llm` (post-deploy)

## Risks

- CSP estricta puede bloquear scripts inline en `agricultor_ia.html` — aplicar CSP en modo report-only primero.
- Sitemap debe listar solo URLs públicas (no rutas autenticadas).
