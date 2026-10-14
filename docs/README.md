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
| **Informe técnico para presentar** | [../documentacion_equipo/entregables/INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.md](../documentacion_equipo/entregables/INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.md) |
| Sustentación / diapositivas | [../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md](../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md) |
| PDF completo | `python3 scripts/generate_proyecto_pdf.py` |

## Por área

### Producto y agronomía
- [producto/VISION-Y-LINEAS-ECOGROW.md](producto/VISION-Y-LINEAS-ECOGROW.md) — EcoGrow = automatización agrícola; torre vegetal + forraje
- [hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md](hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md)

### IoT y hardware
- [../hardware/TALLER.md](../hardware/TALLER.md) — **Orden de taller:** pulir el esquemático hasta dejarlo fabricable
- [../hardware/README.md](../hardware/README.md) — Carpetas de esquema, gerbers y piezas 3D
- [../hardware/schematics/diagrama-electrico.md](../hardware/schematics/diagrama-electrico.md) — Diagrama eléctrico EcoGrow 2.0
- [iot/ROADMAP-AUTOMATIZACION-FASES.md](iot/ROADMAP-AUTOMATIZACION-FASES.md) — **A1 ahora:** bomba por tiempo + nivel; A2 nutrientes después
- [iot/FASE1-ESP32-BOMBA-RELE.md](iot/FASE1-ESP32-BOMBA-RELE.md) — Fase antigua de banco con relé en GPIO 26. No es el montaje de esta torre
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
