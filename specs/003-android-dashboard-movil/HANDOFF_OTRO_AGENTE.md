# Handoff: construir dashboard web y Android nativo EcoGrow

Fecha: 2026-10-12. Ámbito: ECOGROW, AISLADO.
Estado: PLAN APROBADO; IMPLEMENTACIÓN PARCIAL NO VALIDADA.

## Instrucción para el agente constructor

John aprobó construir dos entregables: dashboard web responsive (escritorio y
móvil) y aplicación Android nativa Kotlin/Jetpack Compose, usando las mejoras
documentadas de EcoGrow 2.0. Después aclaró que quiere construir con otro agente.
Continúa desde esta rama, revisa el avance parcial y completa la entrega de forma
autónoma, corrigiendo internamente cada fallo hasta cumplir los criterios.
No vuelvas a preguntar qué sensores contiene el alcance: están en `spec.md`.

Repositorio: https://github.com/elJohn72/proyecto_ecogrow
Rama: `codex/android-dashboard-movil`.
Base inicial: `main`, commit `da94b71`.
Checkout: `~/Repositorios Githup/03-proyectos/proyecto_ecogrow` (disco interno).
Lee `spec.md` y `plan.md` de esta carpeta y la constitución `.specify/memory/constitution.md`.
La numeración 003 de esta rama no autoriza sobrescribir el 003 MQTT del SDD histórico.

## Funciones aprobadas

- Nivel de agua %, litros con capacidad/geometría calibradas, TDS ppm, pH y
  temperatura de agua. EC legacy se muestra por separado; no convertir sin factor.
- Estado/control de bomba, automático/manual, temporizador cascada/reposo.
- Recetas documentadas Lechuga, Espinaca, Albahaca y Frutilla/Fresa.
- Alertas, estado de conexión, antigüedad de lecturas, historial disponible.
- Acceso local WiFi AP/LAN autónomo y adaptación al backend web existente.
- IA asesora; seguridad de bomba determinista y local.

## Avance preservado y limitaciones

### Backend

`blueprints/mobile.py`, `services/mobile_service.py`, `tests/test_mobile.py`;
registro en `app.py`/`blueprints/__init__.py`; CSRF JSON acotado en `shared.py`.
Sesión/login/logout, torres por propietario, detalle, bomba y programación.
No cambia esquema. Consultas SELECT evitan inicialización de tablas en lecturas.
Backend legacy carece de TDS/litros calibrados y acuse físico separado: capabilities
los deshabilitan y órdenes devuelven pendiente. Completar integración 2.0 real.
Dependencias `requirements.txt` instaladas en `.venv`; tests aún no ejecutados.

### Web

Ruta autenticada `/control`, template `mobile_dashboard.html`, CSS/JS específicos,
enlace en `base.html`. `node --check` pasó y render/acceso protegido se probaron
con mocks PRUEBA. No hay verificación visual ni recorrido browser completo.

### Android

Proyecto `android/`: Kotlin/Compose, Gradle Wrapper 8.11.1 con checksum,
AGP 8.9.2, Kotlin 2.1.20, clientes remoto/local y sesión/credenciales en memoria.
`./gradlew help` pasó con JDK17 Homebrew. Build/lint/tests cancelados a solicitud
de cambio de ejecutor. No hay APK validado. Revisar compatibilidad toolchain.
Pendientes conocidos: nombres de recetas UI no coinciden con firmware; refresco
y caducidad de lecturas locales; tests de estado/contrato y UI. Auditar manejo
de redirecciones/cookies, cambio de destino, permisos red local y concurrencia.

### Firmware 2.0

Recuperado desde Drive a `platformio/esp32_ecogrow2/` usando el servicio de lectura
con guard de scope; las credenciales originales se retiraron antes de escribirlo.
Se inició endurecimiento (HTTP Basic configurado localmente, JSON validado,
protección de nivel, lecturas null, DS18B20 y parámetros calibrados explícitos).
Es WIP SIN COMPILAR. Hay nombres heredados `AP_SSID/AP_PASS/STA_SSID/STA_PASS`
todavía sin reconciliar con macros `ECOGROW_*`; corregir antes de compilar.
Instalación PlatformIO espressif32 6.9.0 iniciada; descarga del framework abortada.
Revisar completamente control, GPIO/driver real, calibración, temporizadores,
origen de POST y validación del acuse antes de afirmar que es seguro en hardware.
No flasheado. No hay prueba de bomba ni sensores físicos.

Contrato local recuperado: GET `/api/status`; POST `/api/pump` `{on:boolean}`,
`/api/mode` `{mode:"AUTO"|"MANUAL"}`, `/api/recipe` `{recipe_idx:0..3}` en la
variante WIP. Status: `pump_state`, `pump_mode`, `water_level_ok`, `water_level_pct`,
`water_liters`, `tds_ppm`, `ph_val`, `temp_water`, `time_left_sec`, `alert`, `recipe`.
Revisar consistencia con Android y dashboard local. Estado GPIO no mide caudal.

## Gates obligatorios y comandos

El checkout no tenía CI. Crear checks de Python, Android y firmware que reproduzcan
el runtime validado localmente; usar versiones fijadas y entorno Linux equivalente.

```bash
.venv/bin/python -m unittest discover -s tests -v
node --check static/mobile-dashboard.js
git diff --check
cd android
./gradlew --no-daemon lintDebug testDebugUnitTest assembleDebug
./gradlew --no-daemon connectedDebugAndroidTest
```

Desde raíz, firmware:

```bash
pio run -d platformio/esp32_ecogrow2
c++ -std=c++17 -Iplatformio/esp32_ecogrow2/include platformio/esp32_ecogrow2/tests/safety_test.cpp -o /tmp/ecogrow-safety-test
/tmp/ecogrow-safety-test
```

Pruebas significativas: aislamiento por torre/usuario, CSRF/session expiración,
JSON malformado, valores no finitos, encendido sin nivel válido o con lectura
antigua, pérdida de red, cambio de usuario/destino, duplicación y expiración de
comandos; ausencia de datos nunca cero. Revisar dependencias/secretos y seguridad.
Probar web 360/390/430px y escritorio, Android instalado en emulador/teléfono.
Usar exclusivamente fixtures PRUEBA en local y base temporal. Para validar
integración física, disponer de banco autorizado con ESP32; registrar PENDIENTE
si aún no existe, sin fingir evidencia.

## Protección y cierre

No tocar credenciales, dumps, datos operativos, firmware ya instalado, servidor
de producción ni otros ámbitos. `config.h`, `.env`, `local.properties`, caches,
logs y compilados permanecen fuera de git. Conservar rutas/auth web existentes.
No ampliar a LoRa/PostgreSQL/MQTT ni a dosificación/iluminación en este incremento.

Commit/push enfocados; crear o actualizar PR hacia `main`, adjuntarlo al chat,
esperar checks del HEAD FINAL; corregir y repetir hasta verde. Entregar enlaces
al PR, APK, dashboard de prueba y evidencia real de verificaciones. No declarar
LISTO PARA MERGE con checks pendientes o saltados. Merge/deploy requieren autorización
separada. El avance preservado no está listo para merge ni debe desplegarse.
