# Informe de auditoría total — EcoGrow

**Fecha:** 2026-05-26  
**Alcance:** Aplicación web Flask (UI pública + revisión de código backend)  
**Herramientas:** [skills.sh](https://skills.sh/) (`audit-website`, `seo-audit`), [SquirrelScan](https://squirrelscan.com) v0.0.38, [GitHub Spec Kit](https://github.com/github/spec-kit), pruebas unitarias del proyecto.

---

## Resumen ejecutivo

| Área | Estado | Nota |
|------|--------|------|
| **Crawl automático (6 páginas públicas)** | Nota F (31/100) | Esperable en `http://127.0.0.1` sin HTTPS ni sitemap |
| **Accesibilidad (páginas públicas)** | 99/100 | Buena base HTML |
| **Seguridad de aplicación (código)** | Mejorable | CSRF y auth bien encaminados; bug de `ui_mode`; headers faltantes |
| **Tests automatizados** | 12/12 OK | Suite actual pasa |
| **Spec Kit** | Instalado | Ver `specs/001-auditoria-web/` y comandos `/speckit-*` |

La nota global **31 (F)** de SquirrelScan **no refleja la calidad funcional del panel** (rutas protegidas no fueron rastreadas sin sesión). Sirve como checklist de SEO, rendimiento y despliegue para la capa pública.

---

## 1. Metodología

### 1.1 Skills instalados (skills.sh)

| Skill | Origen | Uso en esta auditoría |
|-------|--------|------------------------|
| `audit-website` | [squirrelscan/skills](https://skills.sh/squirrelscan/skills/audit-website) (~52K installs) | Crawl + 230+ reglas técnicas/SEO/a11y |
| `seo-audit` | [coreyhaines31/marketingskills](https://skills.sh/coreyhaines31/marketingskills/seo-audit) | Marco on-page y priorización SEO |
| `spec-driven-development` | [addyosmani/agent-skills](https://skills.sh/addyosmani/agent-skills/spec-driven-development) | Alineación con flujo spec-first |

CLI instalado: `squirrel` v0.0.38 (`~/.local/bin`).

### 1.2 Spec Kit (github/spec-kit)

- **Specify CLI** instalado vía `uv tool install specify-cli`
- Proyecto inicializado con integración **cursor-agent** (`.cursor/skills/speckit-*`, `.specify/`)
- Artefactos de esta auditoría: `specs/001-auditoria-web/` (spec, plan, tasks)

**Flujo recomendado a partir de ahora:**

1. `/speckit-constitution` — principios del proyecto (plantilla en `.specify/memory/constitution.md`)
2. `/speckit-specify` — nuevas funcionalidades
3. `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`
4. Opcional: `/speckit-checklist`, `/speckit-analyze` antes de implementar

### 1.3 Crawl SquirrelScan

```text
URL:     http://127.0.0.1:5050
Cobertura: surface (máx. 80 páginas)
Páginas: 6 (/, /about, /contactos, /demo, /login, /registro)
Reporte: docs/auditoria/squirrel-report-llm.txt
```

**Limitación:** Sin autenticación no se auditaron `/dashboard`, `/torres`, `/cultivos`, `/sensores`, `/agricultor-ia`, etc. Para auditoría completa del panel: repetir crawl con sesión autenticada o auditar URL de producción (Render) con HTTPS.

---

## 2. Resultados SquirrelScan (capa pública)

### 2.1 Puntuación por categoría

| Categoría | Puntuación |
|-----------|------------|
| Performance | 81 |
| Security | 52 |
| Crawlability | 63 |
| Core SEO | 73 |
| Content | 79 |
| Accessibility | 99 |
| Mobile | 100 |
| Images | 99 |

### 2.2 Errores críticos (fail)

| ID | Hallazgo | Páginas |
|----|----------|---------|
| `crawl/sitemap-exists` | Sin `sitemap.xml` | Sitio |
| `security/https` | Sin HTTPS | Todas (dev local) |
| `perf/compression` | Sin compresión gzip/brotli | 5/6 |

### 2.3 Advertencias prioritarias (SEO / contenido)

| ID | Hallazgo | Acción sugerida |
|----|----------|-----------------|
| `crawl/robots-txt` | Sin `robots.txt` | Añadir ruta Flask o archivo estático |
| `core/meta-title` | Títulos cortos (<30 chars) | Ampliar `{% block title %}` por página |
| `core/meta-description` | Descripción duplicada y corta (59 chars) | Meta única por vista en `base.html` |
| `core/canonical` | Sin URL canónica | `<link rel="canonical">` en producción |
| `core/og-tags` / `twitter-cards` | Sin Open Graph | Meta OG + imagen social |
| `core/favicon` | Sin favicon | `static/favicon.ico` + link en `base.html` |
| `content/heading-hierarchy` | Salto H1→H3 | Insertar H2 en plantillas |
| `content/word-count` | Contenido fino en varias páginas | Ampliar copy en about/contacto/demo |
| `images/dimensions` | `hero.png` sin width/height | Atributos en `index.html` |
| `perf/render-blocking` | 4 CSS bloqueantes (fonts, Bootstrap) | `preload`, subset de fuentes, CSS crítico |
| `perf/cache-headers` | Sin Cache-Control en estáticos | Configurar en gunicorn/nginx o Flask |
| `legal/privacy-policy` | Sin política de privacidad | Página `/privacidad` + enlace en footer |
| `eeat/contact-page` | Contacto no detectado como página dedicada | Mejorar `/contactos` (schema, H1, enlaces) |

### 2.4 Lo que ya está bien (público)

- `lang="es"` en HTML
- Viewport responsive
- Imagen hero con `alt` descriptivo
- Bootstrap con integridad SRI en CDN
- Preconnect a Google Fonts
- Enlaces internos coherentes (salvo `/registro` con pocos enlaces entrantes)

---

## 3. Auditoría de aplicación (código y seguridad)

### 3.1 Autenticación y autorización

| Control | Estado | Detalle |
|---------|--------|---------|
| Flask-Login | OK | Rutas protegidas con `@login_required` |
| Admin por email | OK | `ECOGROW_ADMIN_EMAILS`; tests verifican que no se falsifica modo admin en `/mysql` |
| CSRF en formularios | OK | `register_app_security`; token en plantillas |
| API sensores | OK | Excluida de CSRF; exige `X-API-Token` |
| API Agricultor IA | Parcial | POST JSON; el front envía `X-CSRF-Token` — documentar para clientes API |

### 3.2 Hallazgo crítico — `ui_mode` en plantillas

En `blueprints/shared.py`, el context processor asigna modo admin a **cualquier usuario autenticado**:

```python
"ui_mode": "admin" if current_user.is_authenticated else "user",
```

**Impacto:**

- El conmutador Usuario/Admin muestra siempre “Admin” activo.
- Secciones `{% if ui_mode == 'admin' %}` (historial de ciclos, extras en cultivos/sensores) visibles para usuarios normales.
- Las rutas `/mysql` siguen protegidas por `admin_required` + email — el backend es correcto; la **UI y la confianza del usuario** no lo son.

**Corrección:** Restaurar `session.get("ui_mode", "user")` solo cuando `is_admin_user()` sea verdadero; exponer `is_admin_mode()` en plantillas donde corresponda.

### 3.3 `can_manage` vs modo admin

`can_manage` = cualquier usuario logueado. Botones de crear/editar torres y cultivos visibles para todos los agricultores. Si el diseño es “cada usuario gestiona su finca”, es correcto; si solo admins debían editar, hay desalineación con el nombre del flag.

### 3.4 Configuración y despliegue

| Tema | Riesgo | Recomendación |
|------|--------|----------------|
| `SECRET_KEY` aleatoria si falta env | Medio en dev | Obligatoria en producción (`render.yaml` ya genera) |
| `ECOGROW_SENSOR_API_TOKEN` aleatorio si falta | Alto en multi-instancia | Fijar en Render y en ESP32 |
| `SESSION_COOKIE_SECURE` | OK en Render (`true`) | Mantener |
| Headers CSP, X-Frame-Options | Bajo en dev; medio en prod | Middleware o proxy (Render/nginx) |
| MySQL credenciales en env | OK | No commitear `.env` |
| Migración contraseñas plano | Bajo | Código migra a hash en login |

### 3.5 Arquitectura y mantenibilidad

- Duplicación `Conexión/` vs `conexion/` (reexport): confuso para nuevos contribuidores.
- `form.py` y `forms/` coexisten: unificar imports.
- `Conexión/conexion.py` muy grande (~1800 líneas): considerar dividir por dominio en fases futuras (Spec Kit).

### 3.6 Pruebas

```text
12 tests — OK (login, CSRF, API sensores, permisos admin, formularios protegidos)
```

Cobertura limitada a smoke de rutas; no hay tests E2E de UI ni de integración MySQL real.

---

## 4. Mapa de rutas (inventario)

### Públicas

`/`, `/about`, `/contactos`, `/demo`, `/login`, `/registro`, `/planta/<nombre>`

### Autenticadas (no incluidas en crawl)

`/dashboard`, `/torres/*`, `/cultivos/*`, `/sensores`, `/irrigation`, `/sustainability`, `/agricultor-ia`, `/modo/<mode>`

### Admin

`/mysql`, `/mysql/usuarios/*`, `/mysql/inicializar`

### API

`POST /api/sensores/lectura`, `POST /api/agricultor-ia/chat`, `GET /api/ai_advice/<torre_id>`

---

## 5. Plan de remediación priorizado

### P0 — Seguridad / lógica de negocio

1. Corregir `ui_mode` en `shared.py`
2. Fijar `ECOGROW_SENSOR_API_TOKEN` en todos los entornos de producción
3. Revisar que acciones destructivas (borrar cultivo, inactivar torre) exigen POST + CSRF (ya implementado)

### P1 — SEO y descubrimiento (producción)

1. `robots.txt` y `sitemap.xml`
2. Favicon + meta OG por página
3. Política de privacidad y enlace en footer
4. Títulos y descripciones únicos por vista

### P2 — Rendimiento

1. Dimensiones en `hero.png` + preload LCP
2. Cache-Control en estáticos
3. Compresión en servidor (gunicorn + proxy o WhiteNoise con compresión)

### P3 — Calidad y proceso (Spec Kit)

1. Completar `/speckit-constitution` para EcoGrow
2. Ejecutar `specs/001-auditoria-web/tasks.md` por fases
3. Segunda auditoría Squirrel en URL HTTPS de Render tras despliegue

---

## 6. Archivos generados en esta sesión

| Archivo | Descripción |
|---------|-------------|
| `docs/auditoria/squirrel-report-llm.txt` | Reporte XML/LLM SquirrelScan |
| `docs/auditoria/INFORME-AUDITORIA-TOTAL.md` | Este informe |
| `squirrel.toml` | Configuración de proyecto SquirrelScan |
| `specs/001-auditoria-web/spec.md` | Especificación Spec Kit |
| `specs/001-auditoria-web/plan.md` | Plan técnico |
| `specs/001-auditoria-web/tasks.md` | Tareas accionables |
| `.specify/`, `.cursor/skills/speckit-*` | Tooling Spec Kit |

---

## 7. Próximos pasos sugeridos

1. Auditar **producción** con HTTPS — ver [`CHECKLIST-PRODUCCION.md`](./CHECKLIST-PRODUCCION.md).
2. Configurar `ECOGROW_ADMIN_EMAILS` y `ECOGROW_SENSOR_API_TOKEN` en Render (`render.yaml` ya declara las claves).
3. Opcional: activar CSP en modo enforce tras revisar violaciones del header `Content-Security-Policy-Report-Only`.

---

## 8. Remediación aplicada (2026-05-26)

### Cambios de código

- Fix `ui_mode` / `is_admin_mode` en permisos de UI.
- SEO: `robots.txt`, `sitemap.xml`, `/privacidad`, meta OG, favicon, contenido ampliado.
- Rendimiento: hero optimizado, cache en estáticos, `preconnect` CDN.
- Seguridad: headers X-Frame-Options, CSP-Report-Only, `/health` para monitoreo.
- Tests: **15/15** OK.

### SquirrelScan — antes vs después (páginas públicas, local)

| Métrica | Antes (6 pág.) | Después (7 pág.) |
|---------|----------------|------------------|
| **Global** | 31 (F) | **75 (C)** |
| Core SEO | 73 | **100** |
| Crawlability | 63 | **100** |
| Accessibility | 99 | **100** |
| Content | 79 | **92** |
| Security | 52 | 66 (HTTPS sigue fallando en HTTP local) |

Reporte actual: [`squirrel-report-surface-latest.txt`](./squirrel-report-surface-latest.txt)

Script repetible: `bash scripts/audit-local.sh` (servidor en puerto 5050 por defecto).

### Pendiente (T016)

Auditoría en URL HTTPS de Render — requiere despliegue y URL pública.

---

*Informe generado siguiendo el flujo de `audit-website`, `seo-audit` y GitHub Spec Kit.*
