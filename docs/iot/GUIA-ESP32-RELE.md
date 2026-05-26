# Guía rápida: ESP32 + relé con EcoGrow

Empieza con **un relé** (bomba, lámpara, ventilador) y agrega sensores después con el firmware completo en `platformio/esp32_hidroponico/`.

## Qué necesitas

| Pieza | Notas |
|-------|--------|
| ESP32 DevKit | Cualquier WROOM-32 |
| Módulo relé 1 canal | 5 V, optoacoplado (ej. SRD-05VDC) |
| Fuente 5 V | Para el relé si el ESP no alimenta el bobinado |
| Cables Dupont | Señal + GND |

## Cableado (típico)

```
ESP32 GPIO 26  →  IN del módulo relé
ESP32 GND      →  GND del módulo relé
Relé COM/NO    →  Carga (bomba/luz) según tu montaje
```

Muchos módulos activan con **LOW** en IN (`RELAY_ACTIVE_LOW = true` en `config.h`).

## Software

### 1. EcoGrow (PC o servidor)

```bash
export ECOGROW_SENSOR_API_TOKEN="un-token-largo-secreto"
flask run --host 0.0.0.0 --port 5000
```

1. Regístrate e inicia sesión.
2. Registra una torre con código único (ej. `ECO-TORRE-001`).
3. (Opcional) Asocia un cultivo activo si luego enviarás sensores.

### 2. Firmware relé (`platformio/esp32_rele_base`)

```bash
cd platformio/esp32_rele_base
cp include/config.h.example include/config.h
# Edita WiFi, API_SYNC_URL, API_TOKEN, TORRE_CODIGO, RELAY_PIN
pio run -t upload
pio device monitor
```

### 3. Probar

- En **Monitoreo** → torre seleccionada → **Encender rele** / **Apagar rele**.
- En el monitor serie del ESP32 deberías ver `HTTP 200` y el cambio de estado del relé en ~10 s.

## API IoT

**POST** `/api/iot/sync`  
Header: `X-API-Token: <ECOGROW_SENSOR_API_TOKEN>`

```json
{
  "torre_codigo": "ECO-TORRE-001",
  "dispositivo": "esp32_rele_01",
  "rele_principal": true
}
```

Respuesta:

```json
{
  "ok": true,
  "comandos": { "rele_principal": "encendido" },
  "actuador": { "estado": "encendida", "modo": "manual" }
}
```

Puedes añadir sensores en el mismo JSON (`ph`, `ec`, `nivel_agua`, …) cuando tengas hardware; requiere cultivo activo en la torre.

## Siguiente paso: más sensores

Cuando el relé funcione, migra a `platformio/esp32_hidroponico/`:

- pH, EC, DS18B20, TOF, DHT, BH1750 (ver README de ese proyecto).
- Sigue usando `/api/iot/sync` o `/api/sensores/lectura` para telemetría completa.

## Seguridad

- No subas `config.h` a Git (contiene WiFi y token).
- Usa el mismo `ECOGROW_SENSOR_API_TOKEN` en Flask y en el ESP32.
- En producción (Render), la URL debe ser `https://...` y la IP pública accesible desde tu red o usa un túnel/ngrok para pruebas.
