# EcoGrow 2.0

Sistema integral de hidroponía automatizada: dashboard web responsive, aplicación nativa Android (Kotlin / Jetpack Compose), aprovisionamiento Wi-Fi por BLE (Espressif Protocomm Security 1) y firmware ESP32 con sincronización periódica a Coolify.

---

## 🚀 Arquitectura y Componentes del Sistema

El ecosistema EcoGrow 2.0 se compone de 4 capas integradas con seguridad fail-closed y arquitectura sin intermediarios innecesarios:

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Aplicación Nativa Android   │       │      Dashboard Web Responsive   │
│   (Kotlin / Jetpack Compose)    │       │     (Jinja2 / Bootstrap / JS)   │
└───────────────┬─────────────────┘       └────────────────┬────────────────┘
                │ BLE (Protocomm)                          │ HTTPS / REST
                │ & HTTPS / REST                           │
                ▼                                          ▼
┌───────────────────────────────────────────────────────────────────────────┐
│              Backend Flask & Coolify (VPS Andrés Bello)                   │
│         - API Mobile (/api/mobile/*) con CSRF y comandos con TTL (60s)    │
│         - Sincronización IoT (/api/iot/sync) con Bearer Token & ACK       │
│         - Base de datos MariaDB aislada en red bridge interna             │
└─────────────────────────────────────▲─────────────────────────────────────┘
                                      │ HTTP Sync (WiFi)
                                      │ Telemetría + ACK
┌─────────────────────────────────────┴─────────────────────────────────────┐
│                       Microcontrolador ESP32                              │
│         - Aprovisionamiento BLE (Security 1, PoP ecogrow20)               │
│         - Recuperación física: botón BOOT (GPIO 0) durante 5 segundos     │
│         - Protección local de bomba modular contra rollover de millis()   │
│         - Servidor HTTP local de emergencia (192.168.4.1 / PIN)           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 1. Aplicación Android Nativa (`android/`)
- **Tecnologías:** Kotlin 2.0, Jetpack Compose, Material 3, OkHttp3, Corrutinas y Flow.
- **Aprovisionamiento BLE Oficial:** Integración con `esp-idf-provisioning-android` (v2.4.4) mediante **Security 1** con Curve25519 y Proof of Possession (`ecogrow20`).
- **Selector Wi-Fi Estilo Ezviz:** Descubrimiento de torres en el aire (`PROV_EcoGrow_*`), escaneo de redes 2.4 GHz emitidas por el hardware y transferencia segura de credenciales.
- **Control Dual:** Conexión directa a torre local (`192.168.4.1` con PIN) y sincronización con el servidor Coolify.
- **Recetas Hidropónicas:** Sincronizadas con firmware (Lechuga 10/20m, Espinaca 10/25m, Albahaca 12/20m, Frutilla/Fresa 15/30m).

---

## Hardware (`hardware/`)

Diagrama, pines y armado en baquelita: [hardware/README.md](hardware/README.md). La bomba va por MOSFET en el GPIO 25. El módulo relé no forma parte del montaje.

## ⚡ 2. Firmware ESP32 (`platformio/esp32_ecogrow2/`)
- **Plataforma:** PlatformIO, Framework Arduino ESP32 (v6.9.0), tabla `min_spiffs.csv` (1.9MB app).
- **Protección de Bomba Fail-Closed:** Seguridad local obligatoria. Si el sensor ultrasónico detecta nivel de agua inferior al mínimo (<10%), la bomba se apaga físicamente y se bloquea el encendido.
- **Aritmética Segura de Temporización:** Cálculo modular `cycleElapsed()` con `uint32_t` verificado mediante pruebas unitarias C++ contra rollover de `millis()` (49.7 días).
- **Enlace Remoto Periódico:** Rutina `sincronizarConVps()` reporta telemetría a `/api/iot/sync`, recibe órdenes remotas con validación de expiración (TTL 60s) y emite acuse de recibo ACK.
- **Botón de Rescate:** Mantener pulsado el botón **BOOT (GPIO 0)** durante 5 segundos borra credenciales NVS y reactiva el anuncio BLE para reconfigurar el Wi-Fi.

---

## 🌐 3. Backend Flask & Dashboard Web
- **Tecnologías:** Python 3.11, Flask 3.1.2, Flask-Login, Gunicorn, MySQL Connector, Bootstrap 5.
- **Dashboard Responsive:** Optimizado para escritorio y dispositivos móviles (360px, 390px y 430px) con indicador en vivo de telemetría y elevación visual.
- **Salud del Sistema:** Endpoint `/health` con comprobación en tiempo real de la base de datos MariaDB (`status: ok`, `database: connected`).
- **Comandos con TTL:** Comandos de bomba con UUID único, timestamp y tiempo de vida estricto (60s) para evitar que órdenes viejas se ejecuten al reconectar.

---

## ☁️ 4. Despliegue en Coolify (Laboratorio Andrés Bello)

Desplegado en el VPS Hostinger KVM 2 de la Unidad Educativa Particular Andrés Bello (`179.236.74.107`):

- **URL Pública del Dashboard / API:**  
  [`http://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io`](http://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io)
- **Credenciales de Prueba:**
  - Correo: `prueba@ecogrow.local`
  - Contraseña: `Demo1234!`
  - Torre vinculada: `ECOGROW-01`
- **Base de Datos MariaDB:** Contenedor `ecogrow-db` aislado en red Docker bridge `coolify` (puerto 3306 cerrado hacia internet).
- **Seguridad en Docker:** `Dockerfile` y `.dockerignore` configurados para excluir secretos, cachés y artefactos locales.
- **Monitoreo Continuo:** Health check nativo de Coolify sobre `/health` con reversión automática en caso de falla.

---

## 🛠️ Comandos de Desarrollo y Verificación

### Pruebas Unitarias Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

### Compilación y Tests de Android
```bash
cd android
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew testDebugUnitTest lintDebug assembleDebug
```
*APK generado en:* `android/app/build/outputs/apk/debug/app-debug.apk`

### Compilación y Tests de Firmware ESP32
```bash
# Tests unitarios C++ de seguridad de bomba:
clang++ -std=c++17 -Iplatformio/esp32_ecogrow2/include platformio/esp32_ecogrow2/tests/safety_test.cpp -o /tmp/safety_test && /tmp/safety_test

# Compilación PlatformIO:
pio run -d platformio/esp32_ecogrow2
```

---

## 📋 Estructura del Repositorio

```text
proyecto_ecogrow/
├── android/                             # Aplicación nativa Android (Kotlin / Compose)
│   ├── app/src/main/java/...            # UI, ViewModels, BleProvisioningManager
│   └── build.gradle.kts                 # Configuración AGP 8.9.2 y dependencias
├── platformio/
│   └── esp32_ecogrow2/                  # Firmware oficial ESP32 2.0 (BLE + HTTP Sync)
│       ├── src/main.cpp                 # Lógica de microcontrolador y servidor AP
│       ├── include/safety.h             # Cálculo modular de bomba y seguridad local
│       └── tests/safety_test.cpp        # Suite de pruebas de temporización y rollover
├── blueprints/                          # Módulos Flask (torres, sensores, auth, mobile)
├── domain/                              # Lógica hidropónica y algoritmos de control
├── services/                            # Servicios de datos y comandos móviles con TTL
├── templates/                           # Vistas Jinja2 responsive
├── static/                              # JS y CSS del dashboard móvil
├── database/schema.sql                  # Esquema DDL relacional para MariaDB/MySQL
├── deploy/                              # Configuración Dockerfile y despliegue
├── Dockerfile                           # Definición reproducible de contenedor
└── .github/workflows/
    ├── ci.yml                           # Pipeline de integración continua (Android, C++, Python)
    └── deploy.yml                       # Disparador de despliegue en Coolify
```

---

## 📄 Especificaciones Técnicas

- [Especificación Funcional EcoGrow 2.0](specs/003-android-dashboard-movil/spec.md)
- [Plan de Arquitectura y Verificaciones](specs/003-android-dashboard-movil/plan.md)
- [Matriz de Tareas y Evidencias](specs/003-android-dashboard-movil/tasks.md)
