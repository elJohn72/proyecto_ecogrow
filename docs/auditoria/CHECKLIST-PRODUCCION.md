# Checklist — auditoría en producción (Render)

Sustituye `BASE_URL` por la URL HTTPS real del servicio (ej. `https://proyecto-ecogrow.onrender.com`).

## Variables en Render

- [ ] `SECRET_KEY` generada
- [ ] `SESSION_COOKIE_SECURE=true`
- [ ] `MYSQL_*` configuradas y base accesible
- [ ] `ECOGROW_SENSOR_API_TOKEN` fija (misma en ESP32)
- [ ] `ECOGROW_ADMIN_EMAILS` con correos de administradores

## Comandos

```bash
export BASE_URL="https://TU-SERVICIO.onrender.com"
curl -fsS "${BASE_URL}/health"
curl -fsS "${BASE_URL}/robots.txt" | head
curl -fsS "${BASE_URL}/sitemap.xml" | head

squirrel audit "${BASE_URL}" -C surface -m 80 --format llm \
  -o docs/auditoria/squirrel-report-produccion.txt
```

## Criterios objetivo (post-remediación)

| Métrica | Objetivo intermedio |
|---------|---------------------|
| Core SEO | ≥ 75 |
| Crawlability | ≥ 75 |
| Security (HTTPS) | Sin fallo `security/https` |
| Global | ≥ 60 (luego pulir hacia 85+) |

## Tras el despliegue

1. Actualizar `INFORME-AUDITORIA-TOTAL.md` sección 8 con puntuaciones de producción.
2. Marcar T016 en `specs/001-auditoria-web/tasks.md`.
