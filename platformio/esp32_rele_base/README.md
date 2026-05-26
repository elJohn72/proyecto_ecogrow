# ESP32 DevKit + relé + bomba — Fase 1 IoT

Firmware PlatformIO para **Fase 1**: sincroniza con EcoGrow y controla la **bomba** vía módulo relé.

| Guía | Contenido |
|------|-----------|
| **[FASE1 (recomendada)](../../docs/iot/FASE1-ESP32-BOMBA-RELE.md)** | BOM, cableado, puesta en marcha, troubleshooting |
| [Guía rápida](../../docs/iot/GUIA-ESP32-RELE.md) | Resumen API y prueba panel |

## Inicio rápido

```bash
cd platformio/esp32_rele_base
cp include/config.h.example include/config.h
# Editar WiFi, API_SYNC_URL, API_TOKEN, TORRE_CODIGO
pio run -t upload
pio device monitor -b 115200
```

## Características

- `POST /api/iot/sync` cada 10 s (configurable)
- LED estado GPIO 2 · botón BOOT toggle local (prueba)
- Failsafe: apaga bomba sin WiFi/API
- Placa: `esp32dev` (ESP32 DevKit)

## Prueba API desde PC

```bash
export ECOGROW_SENSOR_API_TOKEN=tu-token
export TORRE_CODIGO=ECO-TORRE-001
bash ../../scripts/test-iot-sync.sh
```
