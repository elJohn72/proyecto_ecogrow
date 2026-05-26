# ESP32 + relé (inicio IoT)

Firmware mínimo para encender/apagar un relé desde EcoGrow.

Documentación completa: [`docs/iot/GUIA-ESP32-RELE.md`](../../docs/iot/GUIA-ESP32-RELE.md)

```bash
cp include/config.h.example include/config.h
pio run -t upload && pio device monitor
```
