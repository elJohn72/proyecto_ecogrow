# Entregables EcoGrow

Material listo para sustentación, docentes o portfolio.

## Archivos principales

| Archivo | Descripción |
|---------|-------------|
| **ECOGROW-DOCUMENTACION-COMPLETA.pdf** | Documento maestro (generado) |
| [../../docs/ESTRUCTURA-PROYECTO.md](../../docs/ESTRUCTURA-PROYECTO.md) | Estructura del repositorio |
| [../../hardware/3d/germinador/README.md](../../hardware/3d/germinador/README.md) | Modelo 3D germinador (`.3mf`) |
| [../presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md](../presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md) | 20 diapositivas |

## Generar / actualizar

```bash
# PDF completo
python3 scripts/generate_proyecto_pdf.py

# Paquete en Descargas (código + docs + ZIP)
bash scripts/exportar_paquete_descargas.sh
```

## Checklist de entrega académica

- [ ] Repositorio público: https://github.com/elJohn72/proyecto_ecogrow
- [ ] PDF en esta carpeta
- [ ] Demo: login → torre → dashboard → monitoreo
- [ ] CRUD cultivos + reporte PDF
- [ ] (Opcional) Demo ESP32 + relé
- [ ] Presentación en `presentaciones/`
