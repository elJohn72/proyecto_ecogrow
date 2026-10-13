# Protocolo de Aprovisionamiento, Recuperación y Ciclo de Vida del PIN PoP (EcoGrow 2.0)

Este documento detalla el procedimiento oficial de entrega, recuperación y ciclo de vida de la identidad criptográfica por dispositivo (Proof of Possession - PoP) para las torres hidropónicas EcoGrow 2.0.

---

## 1. Modelo de Identidad y Entrega al Usuario

Cada torre EcoGrow cuenta con una identidad única e impredecible generada durante el proceso de fabricación y ensamblaje físico:

1. **Nombre de Servicio BLE:** `PROV_EcoGrow_XXXX` (donde `XXXX` corresponde a los 2 últimos octetos hexadecimales de la dirección MAC física del ESP32).
2. **PIN de Posesión (PoP):** Clave criptográficamente impredecible de 8 caracteres alfanuméricos Base32 (`23456789ABCDEFGHJKLMNPQRSTUVWXYZ`), generada mediante generador de números aleatorios seguro (`esp_random()` en firmware o `secrets` en taller).
3. **Etiqueta Física y Código QR:**
   - Durante la fabricación, la herramienta `tools/provision_device.py` genera la etiqueta física en formato SVG vectorial y la imprime para adherirla al chasis de la torre.
   - La etiqueta contiene el texto del PIN en fuente grande legible y el código QR oficial con el payload:
     ```json
     {"ver":"v1","name":"PROV_EcoGrow_XXXX","pop":"ABCDEF12","transport":"ble"}
     ```
   - Nunca se imprimen claves PoP en registros generales ni se derivan de datos públicos ni contraseñas compartidas.

---

## 2. Flujo de Configuración en Android

1. El usuario enciende la torre EcoGrow 2.0.
2. Abre la app Android oficial y selecciona la torre Bluetooth encontrada (`PROV_EcoGrow_XXXX`).
3. Ingresa el PIN PoP impreso en la etiqueta de la torre (o introduce el payload escaneado del QR).
4. La app inicia la sesión autenticada `Security 1` con el SDK de Espressif y envía el SSID y contraseña WiFi del router.
5. El ESP32 valida el PIN de posesión, se conecta al router WiFi, sincroniza hora por SNTP y comienza a transmitir telemetría al backend Coolify mediante HTTPS con validación CA (`ISRG Root X1`).

---

## 3. Separación entre Reconfiguración WiFi y Restablecimiento de Fábrica

El firmware implementa una separación física estricta en el pulsador `BOOT` (GPIO 0):

```
┌────────────────────────────────────────────────────────────────────────┐
│                   PULSACIÓN DEL BOTÓN FÍSICO BOOT                      │
├────────────────────────────────────────────────────────────────────────┤
│ 0 a 2 segundos:    Ignorado (protección contra pulsaciones accidentales│
│ 3 a 8 segundos:    RECONFIGURAR WIFI (Conserva PIN PoP e identidad)     │
│ >= 12 segundos:    RESTABLECIMIENTO DE FÁBRICA TOTAL (Borra NVS)       │
└────────────────────────────────────────────────────────────────────────┘
```

### A. Reconfigurar WiFi (Cambio de router o corrección de clave)
- **Acción:** Mantener presionado el botón `BOOT` entre **3 y 8 segundos** y soltarlo.
- **Efecto:**
  - El ESP32 borra únicamente las credenciales de red WiFi guardadas.
  - **Conserva intacta la memoria NVS:** la clave PoP, las calibraciones de pH/TDS y la identidad de la torre **permanecen inalteradas**.
  - El ESP32 se reinicia y vuelve a activar el aprovisionamiento BLE con el **MISMO PIN impreso en la etiqueta**.
  - **Garantía:** El usuario puede cambiar de router o red WiFi cuantas veces lo necesite sin que la etiqueta física pierda validez.

### B. Restablecimiento de Fábrica (Factory Reset)
- **Acción:** Mantener presionado el botón `BOOT` durante **12 segundos continuos**.
- **Efecto:**
  - El sistema detecta la confirmación prolongada y ejecuta `prefs.clear()`, borrando toda la partición NVS.
  - Se genera una nueva identidad al siguiente encendido virgen.
  - **Autorización:** Solo debe ejecutarse en taller de servicio técnico o al desincorporar una torre.

---

## 4. Herramienta de Fabricación (`tools/provision_device.py`)

Comando para generar una nueva ficha de ensamblaje y etiqueta de chasis:
```bash
python3 tools/provision_device.py generate --mac "CC:50:E3:A1:B2:C3" --out "etiquetas/"
```
Salida generada:
- Ficha técnica de fabricación con Serial, MAC, BLE Name y PoP único.
- Archivo vectorial SVG imprimible (`etiquetas/PROV_EcoGrow_B2C3_etiqueta.svg`) listo para plotter/etiquetadora térmica.
