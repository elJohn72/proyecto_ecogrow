# Tareas de Implementación: EcoGrow 2.0 (Full-Stack, BLE, Android y Coolify)

Fecha: 2026-10-12
Ámbito: ECOGROW, AISLADO
Rama: `codex/ecogrow-full-stack-coolify`
Destino Despliegue: Coolify en VPS Hostinger Andrés Bello (`179.236.74.107`)
Estado general: **EN PROCESO DE ENTREGA FINAL Y DESPLIEGUE EN COOLIFY**

---

## Tarea 1: Aprovisionamiento BLE Oficial en ESP32 y Sincronización VPS [COMPLETADO]
- **Objetivo:** Aprovisionamiento WiFi BLE oficial sin reflashear y enlace bidireccional periódico con el VPS.
- **Archivos:** `platformio/esp32_ecogrow2/src/main.cpp`, `platformio/esp32_ecogrow2/include/safety.h`, `platformio/esp32_ecogrow2/tests/safety_test.cpp`, `platformio/esp32_ecogrow2/include/config.h.example`.
- **Acciones Realizadas:**
  1. Habilitado soporte de `WiFiProv` (Espressif Protocomm / Security 1) con PoP `ecogrow20`.
  2. Implementada rutina de recuperación física: botón BOOT (GPIO 0) durante 5 segundos borra NVS y reactiva BLE `PROV_EcoGrow_XXXX`.
  3. **Corrección de temporización AUTO (Safety):** eliminada resta unsigned propensa a desbordamiento; implementado cálculo modular `cycleElapsed(ahora, timestampCiclo, duracionCicloMs)` y `manualLimitExceeded` con tipo `uint32_t`. Pruebas de rollover C++ validadas al 100%.
  4. **Autenticación local fail-closed:** `authorized()` en servidor HTTP local exige usuario `admin` y contraseña igual al PIN de posesión `BLE_POP` (`ecogrow20`).
  5. **Cliente HTTP periódico hacia VPS:** `sincronizarConVps()` transmite telemetría (`/api/iot/sync`) con Bearer token, procesa comandos remotos de bomba con validación de TTL (60s) y seguridad local (`nivelAguaOk`), y envía confirmación ACK.
- **Evidencia de Verificación:** Compilación con PlatformIO exitosa (Flash 85.2%, RAM 18.2%) y safety tests C++ en código 0.

---

## Tarea 2: Módulo Android Nativo Jetpack Compose & BLE Oficial [COMPLETADO]
- **Objetivo:** Aplicación nativa Kotlin/Compose con aprovisionamiento oficial Espressif, selector de torres y control local/remoto.
- **Archivos:** `android/app/build.gradle.kts`, `android/settings.gradle.kts`, `android/app/src/main/java/com/ecogrow/mobile/BleProvisioningManager.kt`, `android/app/src/main/java/com/ecogrow/mobile/EcoGrowViewModel.kt`, `android/app/src/main/java/com/ecogrow/mobile/MainActivity.kt`.
- **Acciones Realizadas:**
  1. Integrada dependencia oficial `com.github.espressif:esp-idf-provisioning-android:lib-2.4.4` con Jitpack.
  2. Reescrito `BleProvisioningManager` para utilizar `ESPProvisionManager` con Security 1 y escaneo real de redes del microcontrolador (eliminado el mock anterior).
  3. Corregida selección de torres en `EcoGrowViewModel`: autoselección si existe exactamente una torre, pantalla de selección de torre y estados de carga/vacío en `MainActivity`.
  4. Ajustados botones de bomba en Android para permitir detención cuando `reported == null` (modo remoto pendiente de sincronización).
  5. Sincronizadas duraciones de recetas en UI con firmware (`Lechuga 10/20m`, `Espinaca 10/25m`, `Albahaca 12/20m`, `Frutilla 15/30m`).
  6. Conectado callback `onOpenLocalDashboard(ip, pin)` con autenticación segura en diálogo y pantalla principal.
- **Evidencia de Verificación:** `JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew lintDebug testDebugUnitTest assembleDebug` pasó exitosamente con 0 errores y APK generado.

---

## Tarea 3: Backend Flask, Modelos y Control de Comandos con TTL [COMPLETADO]
- **Objetivo:** API robusta, control de comandos con TTL y verificación de base de datos en `/health`.
- **Archivos:** `app.py`, `services/mobile_service.py`, `blueprints/sensores.py`, `Conexión/conexion.py`.
- **Acciones Realizadas:**
  1. Añadido `check_database_readiness()` en `conexion.py` y verificación en `/health` (devuelve 200 si DB ok/mocked, 503 si unreachable).
  2. Implementado ciclo de vida de comandos en `mobile_service.py`: `create_pump_command` con UUID, timestamp, TTL (60s), expiración automática y `record_command_ack`.
  3. Integrado procesamiento de comandos y registro de ACK en `blueprints/sensores.py` (`/api/iot/sync`).
- **Evidencia de Verificación:** 40/40 pruebas unitarias Python pasando en 0.29s. `node --check static/mobile-dashboard.js` OK.

---

## Tarea 4: Seguridad Docker y Despliegue en Coolify (Laboratorio Andrés Bello) [COMPLETADO]
- **Objetivo:** Despliegue reproducible y seguro en Coolify en el VPS Hostinger Andrés Bello (`179.236.74.107`).
- **Archivos:** `Dockerfile`, `deploy/Dockerfile`, `.dockerignore`, `deploy/.dockerignore`, `.github/workflows/deploy.yml`.
- **Acciones Realizadas:**
  1. Exclusión de secretos, cachés y artefactos en `.dockerignore` y `deploy/.dockerignore`.
  2. `Dockerfile` corregido para copiar selectivamente módulos de aplicación y esquema `database/` sin depender de `.env` locales.
  3. Creado recurso MariaDB en Coolify (`ecogrow-db`, UUID `6l4gfctvpucf8ov5wvinw0tz`) en red interna `coolify`.
  4. Creado recurso Application en Coolify (`ecogrow-app`, UUID `w3bmo8epk9iedi7gkqchdpru`) enlazado al repositorio GitHub y rama `codex/ecogrow-full-stack-coolify`.
  5. Inicializadas tablas de base de datos en el contenedor MariaDB mediante `database/schema.sql`.
  6. Inyectadas variables privadas de entorno en Coolify (`MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `ECOGROW_SENSOR_API_TOKEN`, `SECRET_KEY`, `SESSION_COOKIE_SECURE`, `PORT=8000`).
  7. Adaptado workflow `.github/workflows/deploy.yml` para disparar webhook de Coolify.
- **Evidencia de Verificación:** Base de datos activa y saludable en el VPS; API Coolify verificada y configurada.

---

## Tarea 5: Validación Cruzada y Verificaciones de CI [COMPLETADO]
- **Objetivo:** Verificar suite de CI, construir artefactos y validar despliegue activo en Coolify.
- **Acciones Realizadas:**
  1. 43/43 tests Python pasando localmente.
  2. Tests unitarios C++ de seguridad de bomba: 0 errores.
  3. Firmware ESP32 compilado en PlatformIO: OK.
  4. Android Gradle build (`testDebugUnitTest`, `assembleDebug`): OK.
  5. `git diff --check`: 0 errores.

---

## Tarea 6: Remediación de Bloqueos de la 2ª Revisión (Auditoría 2026-10-13) [COMPLETADO]
- **Objetivo:** Corregir los 7 bloqueos auditados en `docs/auditoria/REVISION_COOLIFY_SEGUNDA_2026-10-13.md`.
- **Acciones Realizadas:**
  1. **Aprovisionamiento BLE Robusto:** `BleProvisioningManager.kt` suscrito a `EventBus` para esperar evento oficial `ESPConstants.EVENT_DEVICE_CONNECTED` tras descubrimiento GATT antes de llamar a `provision()`. Manejo de timeout (35s), desconexión, PoP incorrecta y confirmación estricta desde `deviceProvisioningSuccess()`. Eliminado valor por defecto hardcodeado.
  2. **Comandos Persistentes entre Workers:** Tabla `dispositivo_comandos` creada en MySQL/MariaDB. `services/mobile_service.py` persiste órdenes de bomba, modo y receta en base de datos con marcado de órdenes anteriores como `superseded`. Recuperación y ACK seguros frente a múltiples workers de Gunicorn y reinicios del ESP32.
  3. **HTTPS Completo con Let's Encrypt:** FQDN de Coolify configurado a `https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io` con certificado TLS oficial emitido por Let's Encrypt (ISRG Root X1). Firmware ESP32 migrado a `WiFiClientSecure` con validación CA estricta mediante `ISRG_ROOT_X1_CA` y sincronización horaria SNTP (`configTime`).
  4. **Ingesta y Validación de TDS y Litros:** Columnas `tds_ppm` y `volumen_litros` agregadas a `lecturas_sensores` con migración automática en `conexion.py`. Endpoint `/api/iot/sync` persiste TDS y litros reales; `mobile_service.py` mantiene EC y TDS separados y expone litros basados en calibración física.
  5. **Credenciales y PoP por Dispositivo:** Eliminados tokens y contraseñas compartidas/hardcodeadas en código y en `config.h.example`. Derivación de PoP única ligada a hardware (`EG-MAC`) con soporte NVS. Fallo cerrado (fail-closed) si falta configuración o token.
  6. **Modo y Receta Remotos en Android:** Implementados endpoints `POST /api/mobile/towers/<id>/mode` y `POST /api/mobile/towers/<id>/recipe`. `EcoGrowViewModel.kt` soporta tanto modo local (`local?.request`) como remoto (`api.post`) sin excepciones `local!!`.
  7. **Semántica Apagado Remoto en AUTO:** Orden `PUMP_OFF` en firmware ESP32 conmuta `modoActual = MODO_MANUAL` y pone `duracionCicloMs = 0`, evitando reencendido automático tras tiempo de reposo.
- **Evidencia de Verificación:**
  - Tests Python: 43/43 tests pasando (0 errores, 0 fallos).
  - Tests Android: `testDebugUnitTest` pasando y `assembleDebug` completado exitosamente.
  - Compilación Firmware PlatformIO: Exitosa con TLS `WiFiClientSecure` y `ISRG_ROOT_X1_CA`.
  - Servidor Coolify: Certificado TLS Let's Encrypt activo y verificado por HTTPS (HTTP/2 200 OK).

---

## Tarea 7: Remediación de la 3ª Revisión (Seguridad, Persistencia y Consistencia) [COMPLETADO]
- **Objetivo:** Resolver los 5 hallazgos críticos de la tercera auditoría en `docs/auditoria/REVISION_TERCERA_2026-10-13.md`.
- **Acciones Realizadas:**
  1. **PIN/PoP Impredecible por Dispositivo:**
     - En `platformio/esp32_ecogrow2/src/main.cpp`: generación aleatoria con `esp_random()` (charset base32 de 8 caracteres) persistida en NVS (`prefs.putString("pop", ...)`).
     - Eliminada derivación basada en dirección MAC y nombre BLE.
     - Eliminada impresión del PIN/PoP en registros Serial / consola.
     - En Android `MainActivity.kt`: placeholder actualizado para indicar PIN físico de la etiqueta de la torre; no autosugerencia.
  2. **ACK Limitado a la Torre Propietaria:**
     - En `services/mobile_service.py:record_command_ack`: validación estricta de `cmd_id` no vacío, verificación de pertenencia `WHERE id_comando=%s AND torre_id=%s AND estado='pending'`.
     - Validación de transiciones a estados permitidos (`executed`, `rejected`, `expired`).
     - Rechazo de confirmaciones cruzadas entre torres y eliminación de actualizaciones wildcard.
  3. **Persistencia como Única Fuente de Verdad:**
     - Eliminado almacenamiento en memoria `_pending_commands`.
     - Implementada transacción atómica `_execute_transaction` en `Conexión/conexion.py` que ejecuta el marcado `superseded` y el `INSERT` dentro de la misma transacción con rollback ante fallos.
     - Errores de almacenamiento lanzan `MobileError("command_storage_failed", ..., 503)` sin devolver estados ficticios de `pending`.
     - Ordenamiento determinista en `get_active_command` y `get_active_pump_command` por `(creado_en DESC, id_comando DESC)`.
  4. **Separación de Estado Físico de Bomba y Comandos:**
     - `pump.reported` desacoplado de órdenes `SET_MODE` y `SET_RECIPE`: solo refleja `"on"`, `"off"` o `None` proveniente de telemetría de actuador (`reporte_esp32`) o de órdenes de bomba ejecutadas.
     - `SET_MODE` y `SET_RECIPE` se gestionan en sus dominios de modo y receta sin alterar el estado reportado ni deseado de la bomba.
  5. **Volumen Solo con Calibración Explícita:**
     - Agregada columna `deposito_calibrado BOOLEAN NOT NULL DEFAULT FALSE` en `configuracion_control` (`database/schema.sql` y `conexion.py`).
     - En `sync_iot_device`: si no llega volumen directo, solo se calcula a partir del porcentaje si `deposito_calibrado` es verdadero. Caso contrario, se preserva `None` (`SIN_DATO`).
     - Capability `liters` en `tower_detail` exige `deposito_calibrado` activo.
- **Evidencia de Verificación:**
  - Tests Python: 48/48 tests pasando (+5 tests nuevos cubriendo aislamiento multi-torre, rollback/503, separación bomba/modo y calibración de volumen).
  - Tests Android: `testDebugUnitTest` pasando al 100%.
  - Compilación Firmware PlatformIO: Exitosa (Flash: 91.9%, RAM: 18.5%).
  - `git diff --check`: 0 errores.

---

## Tarea 8: Remediación de la 4ª Revisión (Onboarding PoP, Estado Físico Bomba y Multi-worker Gate) [COMPLETADO]
- **Objetivo:** Resolver los bloqueos identificados en la cuarta auditoría en `docs/auditoria/REVISION_CUARTA_2026-10-13.md` (HEAD `e70a26a`).
- **Acciones Realizadas:**
  1. **Entrega y Recuperación de PIN/PoP Bluetooth (P1):**
     - En `platformio/esp32_ecogrow2/src/main.cpp`: separación estricta mediante botón BOOT (GPIO 0):
       - Pulsación entre 3s y 8s: Reconfigura WiFi manteniendo la identidad NVS, calibración y PIN PoP. Permite cambiar de router sin invalidar la etiqueta física de la torre.
       - Pulsación prolongada >= 12s: Restablecimiento de fábrica autorizado físicamente con borrado completo de NVS.
     - Creada herramienta de aprovisionamiento de fábrica `tools/provision_device.py` para generar identificadores, PoP aleatorio Base32, payloads QR JSON y etiquetas vectoriales SVG imprimibles para el chasis de las torres.
     - En Android `MainActivity.kt`: soporte en diálogo BLE para ingreso manual o extracción automática de PIN PoP desde JSON de QR escaneado.
     - Documentación formal en `docs/soporte/RECUPERACION_Y_PROVISIONAMIENTO_POP.md`.
  2. **Estado Físico de Bomba en Modo Manual (P1):**
     - En `Conexión/conexion.py:sync_iot_device`: eliminado `if modo != "manual":` para asegurar que el estado físico reportado (`rele_principal_on`) se persista siempre en `actuadores_torre` con origen `reporte_{dispositivo}` y timestamp en todos los modos.
     - En `services/mobile_service.py:tower_detail`: eliminado el fallback de `reported` a órdenes ejecutadas históricas (`active_pump_cmd.get("status") == "executed"`). `reported` proviene exclusivamente del reporte físico real de la torre.
     - Añadidos tests unitarios validando que tras ON ejecutado y posterior apagado físico por botón o límite de seguridad, ambas interfaces (Web y Android) muestran OFF ("Apagada" / "⚪ DETENIDA").
  3. **Integración Real Multi-Worker y Gate en CI:**
     - Creada suite `tests/test_multiworker_integration.py` que ejecuta procesos independientes del SO (`multiprocessing.Process`) contra una base de datos temporal MariaDB (`ecogrow_temp_test_*`).
     - Cubre los 6 escenarios críticos:
       1. Ciclo de vida real multi-worker: Worker 1 crea orden, Worker 2 lee orden, Worker 3 envía ACK.
       2. Rollback atómico en transacciones ante fallos sin corrupción de comandos previos.
       3. Concurrencia multi-proceso con manejo automático de deadlocks transitorios (error 1213/1205 con backoff exponencial) y orden determinista (`creado_en DESC, id_comando DESC`).
       4. Comandos expirados (`now >= exp`) y superseded rechazan ACKs.
       5. Aislamiento multi-torre: rechazo de ACK de órdenes ajenas.
       6. Persistencia tras reinicio y reconexión sin reejecución de comandos vencidos.
     - Actualizado `.github/workflows/ci.yml` para desplegar el servicio MariaDB en el job `python-web` como gate obligatorio de CI.
- **Evidencia de Verificación:**
  - Tests Python: 56/56 tests pasando (50 unitarios + 6 de integración real multi-worker con MariaDB).
  - Tests Android: `JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew testDebugUnitTest` pasando al 100%.
  - Compilación Firmware PlatformIO: Exitosa (Flash: 91.9%, RAM: 18.5%).
  - Prueba de seguridad en C++: Exitosa (`/tmp/ecogrow-safety-test`).
  - Sintaxis JavaScript: Validada con Node.js (`static/mobile-dashboard.js`).
  - `git diff --check`: 0 errores.
  - Nota de gobernanza: Pruebas físicas en banco real de hardware se conservan formalmente marcadas como pendientes de banco físico autorizado.
