# Documentación EcoGrow

Índice central de la documentación del proyecto.

## Inicio rápido

| Si necesitas… | Lee esto |
|---------------|----------|
| **Visión de producto (2 líneas)** | [producto/VISION-Y-LINEAS-ECOGROW.md](producto/VISION-Y-LINEAS-ECOGROW.md) |
| **Automatización por fases (A0→A3)** | [iot/ROADMAP-AUTOMATIZACION-FASES.md](iot/ROADMAP-AUTOMATIZACION-FASES.md) |
| Visión general y arquitectura | [DOCUMENTACION-PROYECTO-ECOGROW.md](DOCUMENTACION-PROYECTO-ECOGROW.md) |
| Estructura de carpetas y capas | [ESTRUCTURA-PROYECTO.md](ESTRUCTURA-PROYECTO.md) |
| Instalar y ejecutar | [../README.md](../README.md) |
| Sustentación / diapositivas | [../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md](../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md) |
| PDF completo | `python3 scripts/generate_proyecto_pdf.py` |

## Por área

### Producto y agronomía
- [producto/VISION-Y-LINEAS-ECOGROW.md](producto/VISION-Y-LINEAS-ECOGROW.md) — EcoGrow = automatización agrícola; torre vegetal + forraje
- [hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md](hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md)

### IoT y hardware
- [iot/ROADMAP-AUTOMATIZACION-FASES.md](iot/ROADMAP-AUTOMATIZACION-FASES.md) — **A1 ahora:** bomba por tiempo + nivel; A2 nutrientes después
- [iot/FASE1-ESP32-BOMBA-RELE.md](iot/FASE1-ESP32-BOMBA-RELE.md) — A0 (ESP32 + relé + bomba)
- [iot/GUIA-ESP32-RELE.md](iot/GUIA-ESP32-RELE.md) — Resumen API
- [../hardware/3d/germinador/README.md](../hardware/3d/germinador/README.md) — Modelo 3D germinador (.3mf)

### Calidad y despliegue
- [auditoria/CHECKLIST-PRODUCCION.md](auditoria/CHECKLIST-PRODUCCION.md)
- [auditoria/INFORME-AUDITORIA-TOTAL.md](auditoria/INFORME-AUDITORIA-TOTAL.md)

### Especificaciones (Spec Kit)
- [../specs/001-auditoria-web/spec.md](../specs/001-auditoria-web/spec.md)
- [../specs/002-dominio-hidroponia-torre/spec.md](../specs/002-dominio-hidroponia-torre/spec.md)

## Entregables académicos

Carpeta `documentacion_equipo/entregables/`:

- `ECOGROW-DOCUMENTACION-COMPLETA.pdf` — documento maestro
- Generar paquete para Descargas: `bash scripts/exportar_paquete_descargas.sh`
