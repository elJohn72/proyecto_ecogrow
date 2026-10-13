# Protocolo de Aprovisionamiento, Recuperación y Ciclo de Vida del PIN PoP (EcoGrow 2.0)

Este documento detalla el procedimiento oficial de entrega, vinculación en taller, recuperación y ciclo de vida de la identidad criptográfica por dispositivo (Proof of Possession - PoP) para las torres hidropónicas EcoGrow 2.0.

---

## 1. Modelo de Identidad y Vinculación 1:1 en Taller

Cada torre EcoGrow cuenta con una identidad única e impredecible gestionada de forma unificada entre el hardware y su etiqueta física:

1. **Nombre de Servicio BLE:** `PROV_EcoGrow_XXXX` (donde `XXXX` corresponde a los 2 últimos octetos hexadecimales de la dirección MAC física del ESP32).
2. **PIN de Posesión (PoP):** Clave criptográficamente impredecible de 8 caracteres alfanuméricos Base32 (`23456789ABCDEFGHJKLMNPQRSTUVWXYZ`), generada con entropía segura (`esp_random()` en firmware o `secrets` en Python).
3. **Flujo de Taller con Readback Obligatorio:**
   - La herramienta de taller `tools/provision_device.py` se comunica con el ESP32 mediante el protocolo serial UART0.
   - Si el ESP32 ya posee una PoP válida en NVS, la herramienta **la conserva y la lee directamente** (evitando generar dos secretos distintos).
   - Si no existe PoP (o se fuerza con `--force`), la instala en la partición NVS del ESP32.
   - **Verificación obligatoria (Readback):** La herramienta envía un comando de verificación al ESP32. Si el hardware reporta discrepancia, la herramienta **aborta con error y no genera la etiqueta**.
4. **Etiqueta Física y Código QR Matricial:**
   - Una vez confirmada la coincidencia al 100%, la herramienta genera la etiqueta en formato vectorial SVG oficial con permisos restringidos `0600` en `docs/soporte/etiquetas/`.
   - La etiqueta incluye el PIN legible en fuente destacada y un **código QR matricial real escaneable** con el payload JSON oficial:
     ```json
     {"ver":"v1","name":"PROV_EcoGrow_XXXX","pop":"ABCDEF12","transport":"ble"}
     ```
   - Las etiquetas generadas quedan excluidas del repositorio Git (`.gitignore`).

---

## 2. Protocolo Serial de Taller (`UART0` a 115200 baudios)

El firmware responde a comandos de línea que inician con el prefijo `ECOGROW:`:

| Comando | Respuesta ESP32 | Descripción |
| :--- | :--- | :--- |
| `ECOGROW:IDENT?` | `ECOGROW:IDENT:{"mac":"...","ble_name":"...","pop":"...","has_pop":true}` | Consulta la MAC física, nombre BLE y estado de la PoP en NVS sin alterar configuración. |
| `ECOGROW:SET_POP:<token>` | `ECOGROW:SET_POP_OK:{"pop":"..."}` o `ECOGROW:SET_POP_ERR:...` | Programa una clave PoP de 8 caracteres Base32 en NVS y actualiza la credencial activa. |
| `ECOGROW:VERIFY_POP:<token>`| `ECOGROW:VERIFY:{"match":true/false}` | Compara byte a byte el token indicado con el valor almacenado en NVS. |
| `ECOGROW:FACTORY_RESET` | `ECOGROW:RESET_OK` | Borra la NVS completa (`prefs.clear()`), desconecta WiFi y reinicia el SoC. |

---

## 3. Comandos de la Herramienta de Taller (`tools/provision_device.py`)

### A. Aprovisionar y Emitir Etiqueta con Verificación en Hardware
Detecta automáticamente el puerto serial del ESP32, verifica o instala la PoP y emite la etiqueta SVG:
```bash
python3 tools/provision_device.py provision
```
*Opciones:*
- `--port /dev/cu.usbserial-XXXX`: Especificar puerto explícito.
- `--force`: Sobreescribir la PoP en caso de que ya existiera en NVS.
- `--out docs/soporte/etiquetas`: Carpeta de destino para los artefactos.

### B. Verificar Coincidencia entre ESP32 y Etiqueta Impresa
Comprueba que una etiqueta SVG generada o un PIN manual coincida exactamente con el hardware conectado:
```bash
# Verificar contra archivo de etiqueta SVG
python3 tools/provision_device.py verify --label docs/soporte/etiquetas/PROV_EcoGrow_70C4_etiqueta.svg

# Verificar contra PIN de 8 caracteres
python3 tools/provision_device.py verify --pop "A7K9M2PX"
```

### C. Leer Identidad Técnica sin Modificar
```bash
python3 tools/provision_device.py read
```

### D. Modo Offline (Generar Etiqueta para Pruebas de Software)
```bash
python3 tools/provision_device.py generate --mac "44:1D:64:F8:70:C4" --pop "A7K9M2PX"
```

---

## 4. Separación entre Reconfiguración WiFi y Restablecimiento de Fábrica

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
