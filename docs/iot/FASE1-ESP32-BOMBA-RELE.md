# Fase 1 — ESP32 DevKit + relé + bomba (PlatformIO)

Guía práctica para la **primera integración física** con EcoGrow: solo control de bomba vía relé. Los sensores van en **fase 2** (`platformio/esp32_hidroponico/`).

---

## 1. Qué vas a lograr

| Componente | Función |
|------------|---------|
| **ESP32 DevKit** | WiFi + lógica + sync con EcoGrow cada 10 s |
| **Módulo relé 1 canal** | Aísla el ESP32 de la corriente de la bomba |
| **Bomba sumergible / peristáltica** | Riego; alimentación **externa** (no desde el ESP32) |
| **EcoGrow (Flask)** | Panel web → Encender/Apagar rele → ESP32 aplica en la siguiente sync |

---

## 2. Lista de materiales (BOM)

| Pieza | Cantidad | Notas |
|-------|----------|--------|
| ESP32 DevKit (WROOM-32) | 1 | USB para programar |
| Módulo relé 1 ch (5 V, optoacoplado) | 1 | Ej. SRD-05VDC-SL-C |
| Fuente 5 V ≥ 2 A | 1 | Para ESP32 + bobina del relé |
| Fuente bomba (12 V o la de tu bomba) | 1 | Separada del ESP32 |
| Bomba DC | 1 | Según depósito de la torre |
| Cables Dupont | varios | Señal + alimentación |
| (Opcional) Bornera / regleta | 1 | Para COM/NO/NC del relé |

---

## 3. Cableado recomendado

### 3.1 ESP32 ↔ módulo relé (señal)

```text
ESP32 3.3V (o 5V del USB)  →  VCC del modulo rele   (si el modulo acepta 5V en VCC)
ESP32 GND                  →  GND del modulo rele
ESP32 GPIO 26              →  IN del modulo rele
```

> Si el módulo relé exige 5 V en VCC, alimenta VCC del relé desde la fuente 5 V (GND común con ESP32).

### 3.2 Relé ↔ bomba (potencia)

```text
Fuente bomba (+)  →  Bomba (+)
Fuente bomba (-)  →  COM del rele
NO del rele       →  Bomba (-)
```

Con el relé **abierto**, la bomba está apagada. Al **cerrar** NO (rele activado), circula corriente.

```text
        +12V (fuente bomba)
          |
          +---- Bomba ----+
                          |
                         NO (rele)
                          |
                         COM ---- GND fuente bomba
```

**Nunca** conectes la bomba directo a un pin del ESP32.

### 3.3 Diagrama general

```text
  [PC / Render]                    [Red WiFi]
       |                                |
       | HTTPS/HTTP                     |
       v                                v
  +-----------+    POST /api/iot/sync   +-------------+
  |  EcoGrow  | <--------------------> |   ESP32     |
  |  Flask    |                        |  GPIO 26    |
  +-----------+                        +------+------+
                                              |
                                              v
                                       +-------------+
                                       | Modulo rele |
                                       +------+------+
                                              |
                                              v
                                       +-------------+
                                       |   Bomba     |
                                       | (fuente 12V)|
                                       +-------------+
```

---

## 4. Software — orden de puesta en marcha

### Paso A — EcoGrow en el PC (misma red que el ESP32)

```bash
cd proyecto_ecogrow
source venv/bin/activate
export ECOGROW_SENSOR_API_TOKEN="mi-token-secreto-largo"
export SECRET_KEY="otra-clave"
flask run --host 0.0.0.0 --port 5000
```

1. Registro / login en `http://<IP-PC>:5000`
2. **Registrar torre** con código exacto, ej. `ECO-TORRE-001`
3. Anota la IP del PC: `ipconfig` (Windows) o `ip addr` (Linux/Mac)

### Paso B — Firmware PlatformIO

```bash
cd platformio/esp32_rele_base
cp include/config.h.example include/config.h
```

Edita `include/config.h`:

| Variable | Ejemplo |
|----------|---------|
| `WIFI_SSID` / `WIFI_PASSWORD` | Tu red |
| `API_SYNC_URL` | `http://192.168.1.50:5000/api/iot/sync` |
| `API_TOKEN` | Igual que `ECOGROW_SENSOR_API_TOKEN` |
| `TORRE_CODIGO` | Igual que en la web |
| `RELAY_PIN` | `26` (o el GPIO que uses) |
| `RELAY_ACTIVE_LOW` | `true` en módulos típicos |

Compilar y subir:

```bash
pio run -t upload
pio device monitor -b 115200
```

### Paso C — Probar desde el panel

1. **Monitoreo** → torre activa
2. **Encender rele** / **Apagar rele**
3. En el monitor serie (~10 s):

```text
[api] HTTP 200
[rele] ENCENDIDO (bomba ON)
```

### Paso D — Probar con curl (sin ESP32)

```bash
export TOKEN="mi-token-secreto-largo"
curl -s -X POST "http://127.0.0.1:5000/api/iot/sync" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d '{"torre_codigo":"ECO-TORRE-001","dispositivo":"test","rele_principal":false}' | jq
```

---

## 5. Comportamiento del firmware (fase 1)

| Función | Descripción |
|---------|-------------|
| Sync periódico | Cada `SYNC_INTERVAL_MS` (default 10 s) |
| Comando servidor | Aplica `comandos.rele_principal` (`encendido` / `apagado`) |
| Modo manual web | Panel pone `bomba_principal` en manual; ESP obedece en el siguiente sync |
| LED GPIO 2 | Encendido = WiFi OK; parpadeo = error |
| Botón BOOT (GPIO 0) | Toggle local solo para pruebas de banco |
| **Failsafe** | Si no hay WiFi 2 min o API 90 s, **apaga bomba** |

---

## 6. Sugerencias y buenas prácticas

### Hardware

1. **GND común** entre fuente ESP32, fuente bomba y módulo relé.
2. Bomba con **caudal acorde** al depósito (referencia EcoGrow: 5 L, head ≤ 1.4 m).
3. Instala **filtro** en succión y evita funcionar en seco (failsafe ayuda, no sustituye sonda de nivel).
4. Relé con **optoacoplador**; si escuchas “clack” pero la bomba no arranca, revisa COM/NO y la fuente de la bomba.

### Red

1. ESP32 y PC en la **misma VLAN**; evita redes invitado que aíslen clientes.
2. En Render: usa `https://...` y abre firewall; para laboratorio local es más simple **Flask en PC**.
3. Firewall del PC: permitir puerto **5000** entrante en la LAN.

### Software

1. No subas `include/config.h` a Git.
2. Token largo y aleatorio; mismo en Flask y ESP32.
3. Cuando funcione el relé, **fase 2**: sensores en `esp32_hidroponico/` (misma API `/api/iot/sync`).

### Seguridad eléctrica

- Agua + electricidad: bomba y fuentes **fuera** del alcance de salpicaduras.
- Usa regleta con fusible o protección térmica en la línea de la bomba.

---

## 7. Solución de problemas

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `HTTP 401` | Token distinto | Igualar `API_TOKEN` y `ECOGROW_SENSOR_API_TOKEN` |
| `HTTP 400` torre | Código incorrecto | Mismo `TORRE_CODIGO` que en registro web |
| `HTTP -1` / timeout | IP o firewall | `ping` a PC; `flask run --host 0.0.0.0` |
| Relé clic pero bomba no | Cableado potencia | Revisar COM/NO y fuente 12 V |
| Bomba siempre ON | `RELAY_ACTIVE_LOW` invertido | Probar `false` en config |
| Bomba se apaga sola | Failsafe | Revisar WiFi estable o subir `API_FAILSAFE_MS` |
| Panel no cambia rele | Modo / sync | Esperar 10 s; revisar serie `[api] bomba BD` |

---

## 8. Siguiente fase (cuando fase 1 esté estable)

| Fase | Contenido |
|------|-----------|
| **1 (actual)** | ESP32 + relé + bomba + `/api/iot/sync` |
| **2** | pH, EC, DS18B20, nivel TOF, DHT, lux → `esp32_hidroponico` |
| **3** | Riego automático por programa ON/OFF desde BD + nivel mínimo |

---

## Referencias

- Firmware: `platformio/esp32_rele_base/`
- Guía corta: [`GUIA-ESP32-RELE.md`](GUIA-ESP32-RELE.md)
- API backend: `blueprints/sensores.py` → `POST /api/iot/sync`
- Documentación general: [`../DOCUMENTACION-PROYECTO-ECOGROW.md`](../DOCUMENTACION-PROYECTO-ECOGROW.md)
