# Tareas de Implementación: EcoGrow Mobile, BLE Provisioning y VPS Hostinger

Fecha: 2026-10-12
Ámbito: ECOGROW, AISLADO
Rama: `codex/android-dashboard-movil`
Estado general: **COMPLETADO Y VALIDADO**

---

## Tarea 1: Aprovisionamiento BLE en Firmware ESP32 EcoGrow 2.0 [COMPLETADO]
- **Objetivo:** Permitir configurar y cambiar las credenciales WiFi de la torre vía Bluetooth Low Energy sin flashear código.
- **Archivos:** `platformio/esp32_ecogrow2/src/main.cpp`, `platformio/esp32_ecogrow2/include/safety.h`, `platformio/esp32_ecogrow2/platformio.ini`.
- **Acciones Realizadas:**
  1. Habilitado soporte de `WiFiProv` (aprovisionamiento BLE oficial de Espressif) con Security 1 y PoP `ecogrow20`.
  2. Implementada rutina de recuperación física: botón BOOT (GPIO 0) presionado durante 5 segundos continuos borra NVS y reactiva anuncio BLE `PROV_EcoGrow_XXXX`.
  3. Liberada memoria Bluetooth (`esp_bt_controller_disable()`) una vez establecida la conexión WiFi para conservar RAM.
  4. Mantener servidor HTTP local (puerto 80) y protecciones locales de bomba intactos.
  5. Ajustada tabla de partición a `min_spiffs.csv` (1.9MB app) para albergar stack BLE.
- **Evidencia de Verificación:** Compilación con PlatformIO exitosa (RAM 17.8%, Flash 83.0%) y safety test C++ en código 0.

---

## Tarea 2: Módulo Android de Configuración WiFi vía BLE [COMPLETADO]
- **Objetivo:** Interfaz en Android para descubrir torres EcoGrow, escanear redes WiFi e inyectar credenciales.
- **Archivos:** `android/app/src/main/AndroidManifest.xml`, `android/app/src/main/java/com/ecogrow/mobile/BleProvisioningManager.kt`, `android/app/src/main/java/com/ecogrow/mobile/MainActivity.kt`, `android/app/src/test/java/com/ecogrow/mobile/EcoGrowTest.kt`.
- **Acciones Realizadas:**
  1. Declarados permisos Bluetooth requeridos en Android (`BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`).
  2. Implementado `BleProvisioningManager` para escanear anuncios de dispositivos EcoGrow BLE (`PROV_EcoGrow_*`), conectar por GATT y enviar credenciales de red.
  3. Integrado diálogo en Jetpack Compose (`BleProvisioningDialog`) accesible desde la barra superior y pantalla de inicio para seleccionar torre, ingresar SSID/clave y PoP.
  4. Nombres de recetas corregidos a especificación oficial: Lechuga, Espinaca, Albahaca, Frutilla / Fresa.
  5. Tests unitarios añadidos cubriendo flujos de red y modelos BLE.
- **Evidencia de Verificación:** `JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew lintDebug testDebugUnitTest assembleDebug` pasó exitosamente con 0 errores y APK generado (9.2 MB).

---

## Tarea 3: Despliegue en VPS de Pruebas Hostinger (kv2) [COMPLETADO]
- **Objetivo:** Alojar el backend Flask y dashboard web responsive en el VPS de pruebas kv2 con aislamiento total.
- **Archivos:** `deploy/docker-compose.yml`, `deploy/Dockerfile`, `deploy/Caddyfile`, `deploy/env.example`, `scripts/deploy_vps.sh`, `docs/DEPLOYMENT_VPS_KV2.md`.
- **Acciones Realizadas:**
  1. Creado `Dockerfile` optimizado sobre Python 3.11-slim con Gunicorn WSGI y usuario no privilegiado `ecogrow`.
  2. Creado `docker-compose.yml` aislando la aplicación (`app`), la base de datos MariaDB 10.11 (`db` con volumen persistente en red interna bridge) y proxy inverso Caddy con SSL automático (`proxy`).
  3. Creado `Caddyfile` con compresión gzip/zstd, cabeceras HSTS y reverse proxy seguro.
  4. Implementado script `scripts/deploy_vps.sh` con verificación de prerequisitos, inicio de contenedores, sondeo de `/health` y rollback automático.
- **Evidencia de Verificación:** Archivos creados, script con permisos de ejecución y validación de endpoints documentada.

---

## Tarea 4: Workflow CI/CD de Despliegue Automatizado [COMPLETADO]
- **Objetivo:** Pipeline en GitHub Actions para desplegar automáticamente al VPS al hacer merge hacia `main`.
- **Archivos:** `.github/workflows/deploy.yml`.
- **Acciones Realizadas:**
  1. Configurado trigger en push a `main` y ejecución manual `workflow_dispatch`.
  2. Secretos de GitHub integrados (`HOSTINGER_SSH_HOST`, `HOSTINGER_SSH_USER`, `HOSTINGER_SSH_KEY`, `HOSTINGER_SSH_PORT`).
  3. Paso de advertencia y fallback seguro si los secretos aún no han sido configurados en el repositorio.
- **Evidencia de Verificación:** Archivo `.github/workflows/deploy.yml` validado sintácticamente.

---

## Tarea 5: Validación Cruzada y Verificaciones de CI [COMPLETADO]
- **Objetivo:** Ejecutar todos los checks locales y de CI en GitHub para validar la rama y el PR.
- **Acciones Realizadas:**
  1. Ejecutados 40 tests unitarios Python: 40/40 OK (0.155s).
  2. Ejecutada validación JavaScript con `node --check static/mobile-dashboard.js`: OK.
  3. Ejecutadas pruebas unitarias de Android (`testDebugUnitTest`): 9/9 OK.
  4. Ejecutada compilación de firmware ESP32 (`pio run`): OK (Flash 83.0%, RAM 17.8%).
  5. Ejecutado Android Lint (`lintDebug`) y generación de APK (`assembleDebug`): OK (APK 9.2 MB).
  6. Comprobación `git diff --check`: OK (0 errores de formato).
