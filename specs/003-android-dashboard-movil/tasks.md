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
