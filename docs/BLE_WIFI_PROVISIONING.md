# Aprovisionamiento WiFi mediante Bluetooth BLE en EcoGrow 2.0

Este documento describe la arquitectura y el procedimiento operativo para configurar la red WiFi de las torres EcoGrow 2.0 mediante Bluetooth Low Energy (BLE) desde la aplicación Android nativa, sin necesidad de recompilar ni flashear el ESP32.

---

## 1. Arquitectura Técnica

```text
[ App Android EcoGrow ]
       │  (BLE - GATT)
       ▼  Unified Provisioning (Security 1, PoP: ecogrow20)
[ ESP32 EcoGrow 2.0 ]
       │  Guarda credenciales en NVS
       │  Apaga Bluetooth (libera RAM btdm)
       ▼  (WiFi 2.4 GHz)
[ Router / Red Local ]
       ▼  (HTTPS)
[ VPS kv2 EcoGrow Backend ] (Dashboard & API)
```

- **Mecanismo oficial:** Espressif `WiFiProv.h` (`WIFI_PROV_SCHEME_BLE`).
- **Nombre de difusión BLE:** `PROV_EcoGrow_XXXX` (donde `XXXX` corresponde a los últimos dos bytes de la MAC).
- **Esquema de seguridad:** Security 1 con clave de posesión (Proof of Possession - PoP) predeterminada `ecogrow20`.
- **Persistencia:** Las credenciales WiFi se guardan en la memoria no volátil (NVS) del ESP32.
- **Optimización de memoria:** Una vez establecida la conexión WiFi, el stack Bluetooth se detiene y la memoria RAM (`btdm`) se libera para los sensores y control de bombeo.

---

## 2. Procedimiento de Configuración desde la App Android

1. **Requisitos previos:**
   - Teléfono Android con Bluetooth activado y permisos de ubicación/escaneo concedidos.
   - Torre EcoGrow 2.0 encendida.
2. **Paso a paso:**
   - Abrir la app **EcoGrow** en Android.
   - En la esquina superior derecha o en la pantalla de bienvenida, pulsar el botón **📶 BLE** o **Configurar WiFi torre (BLE)**.
   - Pulsar **Buscar torres**. La app listará los dispositivos con prefijo `PROV_EcoGrow_...` y su intensidad de señal (RSSI).
   - Seleccionar la torre detectada.
   - Introducir el nombre de la red WiFi (SSID de 2.4 GHz) y su contraseña.
   - Confirmar o mantener la clave PoP (`ecogrow20`).
   - Pulsar **Enviar configuración a torre**.
   - El ESP32 recibirá las credenciales, verificará la conexión a la red y reportará éxito.

---

## 3. Botón Físico de Recuperación / Cambio de Router

Si la torre cambia de ubicación, el router se reemplaza o la contraseña de la red cambia, no es necesario abrir el gabinete ni reflashear el microcontrolador:

1. Ubicar el botón físico **BOOT** (conectado a **GPIO 0** del ESP32).
2. Con la torre encendida, **mantener pulsado el botón durante 5 segundos continuos**.
3. El ESP32 detectará la pulsación sostenida, imprimirá en consola:
   ```text
   [RESET] Boton presionado por 5s. Borrando credenciales WiFi de NVS...
   ```
4. El dispositivo reiniciará inmediatamente en modo aprovisionamiento BLE, emitiendo de nuevo su señal `PROV_EcoGrow_XXXX`.
5. Abrir la app Android y reconfigurar la nueva red WiFi.

---

## 4. Particionamiento de Memoria en PlatformIO

Dado que el stack BLE de ESP32 requiere aproximadamente 1.6 MB de espacio de programa, se utiliza la tabla de particiones `min_spiffs.csv` (1.9 MB de aplicación), configurada en `platformio.ini`:
```ini
board_build.partitions = min_spiffs.csv
```
Resultados de compilación verificados:
- **RAM:** ~17.8% ocupada.
- **Flash:** ~83.0% ocupada (1,632,593 bytes de 1,966,080 bytes disponibles).
