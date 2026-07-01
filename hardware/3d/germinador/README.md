# Germinador EcoGrow — modelo 3D

Estación de germinación para el sistema hidropónico EcoGrow (fase **P3** del manual de dominio: bandeja antes de la torre vertical).

## Archivo

| Archivo | Formato | Tamaño aprox. |
|---------|---------|---------------|
| `estacion_germinacion_hidroponico.3mf` | 3MF (impresión 3D) | ~3.1 MB |

**Origen:** modelo aportado al proyecto el 2026-06-30 (nombre original: *Estación de Germinación Sistema hidropónico*).

## Uso

1. Abrir el `.3mf` en **PrusaSlicer**, **Bambu Studio**, **Cura** u otro slicer compatible con 3MF.
2. Revisar orientación, soportes y relleno según el material (PLA/PETG recomendado para piezas en ambiente húmedo; validar con el equipo).
3. Imprimir y ensamblar según el diseño; integrar en el flujo **Germinación → plántula → torre** descrito en `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`.

## Relación con el sistema

- **Dominio:** perfil de germinación (pH 5.8–6.2, EC 0.6–1.0) en `domain/hidroponia_torre.py` y manual hidropónico.
- **Hardware IoT:** sensores/actuadores de la torre viven en `platformio/`; el germinador es pieza física complementaria, no firmware en esta carpeta.

## Pendiente (diseño / operación)

- [ ] Fotos del ensamblaje impreso en el repo o entregables
- [ ] BOM de consumibles (bandejas, sustrato, tapa)
- [ ] Integración documentada con el ciclo de cultivo en panel web (opcional)
