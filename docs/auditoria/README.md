# Auditorías EcoGrow

## Informes

| Archivo | Contenido |
|---------|-----------|
| [INFORME-AUDITORIA-TOTAL.md](./INFORME-AUDITORIA-TOTAL.md) | Informe consolidado (código + SquirrelScan) |
| [squirrel-report-llm.txt](./squirrel-report-llm.txt) | Auditoría inicial (pre-fix) |
| [squirrel-report-surface-latest.txt](./squirrel-report-surface-latest.txt) | Auditoría surface post-remediación (nota 75/C) |
| [CHECKLIST-PRODUCCION.md](./CHECKLIST-PRODUCCION.md) | Pasos para auditar Render con HTTPS |

## Repetir auditoría

```bash
# Terminal 1
FLASK_APP=app.py flask run --port 5050

# Terminal 2
bash scripts/audit-local.sh
```

Producción (sustituir URL):

```bash
squirrel audit https://TU-APP.onrender.com -C surface --format llm
```

## Spec Kit

Plan de remediación: `specs/001-auditoria-web/`

Comandos en Cursor Agent: `/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`

## Skills usados

- https://skills.sh/squirrelscan/skills/audit-website
- https://skills.sh/coreyhaines31/marketingskills/seo-audit
- https://skills.sh/addyosmani/agent-skills/spec-driven-development
