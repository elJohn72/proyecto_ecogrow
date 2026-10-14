# Procedimiento de Migración de Identidades Antiguas EcoGrow 2.0

Ámbito: **ECOGROW**, **AISLADO**.

---

## 1. Contexto y Origen del Problema

Durante las primeras fases de desarrollo y pruebas de prototipos (firmware v1 y primeros builds de laboratorio), se utilizaron identificadores genéricos por defecto como:
- `TORRE-001`
- `EG-TORRE-01`
- `DUMMY`
- `PRUEBA`
- `TEST`

Si una placa física fue aprovisionada en el pasado con uno de estos identificadores, el código quedaba persistido en la memoria no volátil (NVS) del ESP32 bajo la clave `torre_code`.

El estándar de producción EcoGrow 2.0 exige:
1. **Unicidad e Inmutabilidad:** Cada torre debe poseer un código canónico derivado de los últimos 6 dígitos hexadecimales de su dirección MAC física (`EG-TORRE-<HEX>`), o un serial de fabricación debidamente asignado.
2. **Coherencia Etiqueta / Hardware / Cloud:** El código impreso en la etiqueta SVG/QR física debe coincidir exactamente con el valor que el ESP32 reporta por serial/BLE y con el registrado en `dispositivos_iot` en la base de datos de producción.

---

## 2. Capas de Migración Implementadas

### Capa A: Auto-migración en Firmware (`main.cpp`)

El firmware del ESP32 ahora incluye la función `esCodigoValido()`:
- Valida longitud (3 a 64 caracteres).
- Rechaza expresamente cualquier placeholder conocido (`TORRE-001`, `EG-TORRE-01`, `DUMMY`, etc.).

Al llamar a `getTorreCodigo()` en el arranque o durante el comando `ECOGROW:IDENT?`:
1. Si el código en NVS es un placeholder o está corrupto, la validación falla.
2. El firmware calcula automáticamente el código canónico a partir de la MAC WiFi de la placa (`EG-TORRE-%02X%02X%02X`).
3. El código canónico se guarda de inmediato en NVS (`prefs.putString("torre_code", derived)`).
4. El comando serial `ECOGROW:SET_CODE:` rechaza cualquier intento de volver a programar un placeholder.

### Capa B: Herramienta de Taller (`tools/provision_device.py`)

Al conectar una placa por USB y ejecutar:
```bash
python3 tools/provision_device.py provision
```
1. **Preflight sin mutación:** Consulta la identidad del ESP32. Si el código reportado es placeholder, deriva inmediatamente el canónico.
2. Comprueba en la base de datos si ya existe un registro reclamado por un usuario antes de escribir en el hardware.
3. Actualiza el código en el hardware con `SET_CODE`, verifica coincidencia con `VERIFY_CODE`, y genera la etiqueta SVG correspondiente con QR y clave PoP protegida.

### Capa C: Migración Idempotente de Base de Datos (`tools/migrate_identities.py`)

Para el parque de dispositivos ya registrados en la base de datos central:

#### 1. Auditoría (Solo lectura / Diagnóstico)
```bash
python3 tools/migrate_identities.py --audit
```
Muestra un reporte detallado indicando qué registros tienen identificadores no canónicos, su dirección MAC, y la acción sugerida.

#### 2. Simulación (Dry-Run por defecto)
```bash
python3 tools/migrate_identities.py --dry-run
```
Calcula la transformación de `TORRE-001` a `EG-TORRE-<HEX>`, comprueba colisiones y confirma que no haya registros duplicados.

#### 3. Aplicación en Base de Datos
```bash
python3 tools/migrate_identities.py --apply
```
- Actualiza atómicamente la tabla `dispositivos_iot`.
- Actualiza la tabla `torres` conservando la vinculación de usuario (`reclamado_por` / `usuario_id`), histórico de telemetría y configuración de bomba/nutrientes.

---

## 3. Checklist de Taller para Unidades en Reparación o Mantenimiento

Cuando un cliente o unidad de campo ingrese al taller:
1. Conectar por cable USB a la estación de trabajo.
2. Ejecutar lectura de identidad:
   ```bash
   python3 tools/provision_device.py verify
   ```
3. Si la etiqueta física está deteriorada o indica un código antiguo (`TORRE-001`):
   ```bash
   python3 tools/provision_device.py provision
   ```
4. Imprimir la nueva etiqueta generada en `docs/soporte/etiquetas/` y adherirla a la torre.
5. Si la torre ya pertenecía a un cliente, verificar que el código en su aplicación móvil o base de datos coincida ejecutando `tools/migrate_identities.py --apply`.
