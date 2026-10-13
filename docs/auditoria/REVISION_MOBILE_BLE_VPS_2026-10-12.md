# Revisión EcoGrow: web, Android, BLE y VPS

Fecha: 2026-10-12. Ámbito: ECOGROW, AISLADO.
Código revisado: `6ea2de6f53b59ff4a7c6567cdb61604b27c49730` en main.
Resultado: NO LISTO COMO ENTREGA COMPLETA. Se revisó código y CI; no se operó
hardware ni servidor, ni se leyeron credenciales locales. Esta revisión no aplica parches.

## Evidencia de validación

- [CI del HEAD revisado](https://github.com/elJohn72/proyecto_ecogrow/actions/runs/38321380696):
  backend/web, build/lint/tests Android y compilación/test de seguridad firmware pasan.
- 40 unittest Python ejecutadas localmente: pasan con operaciones DB simuladas.
- [Deploy del merge](https://github.com/elJohn72/proyecto_ecogrow/actions/runs/38314760447):
  resultado global success, pero paso `Deploy via SSH` SKIPPED. Esto no demuestra
  despliegue en Hostinger. No se comprobó servidor ni URL real.
- PR #1 fusionado; existen commits posteriores incluidos en esta revisión.
- Compilación y mocks no validan aprovisionamiento físico, comunicación remota
  ni actuación segura de bomba. El estado COMPLETADO Y VALIDADO de tasks.md
  debe corregirse hasta completar esas verificaciones.

## Hallazgos prioritarios

### P1 · Aprovisionamiento BLE simulado

`android/app/src/main/java/com/ecogrow/mobile/BleProvisioningManager.kt:189–201`.
Tras descubrir servicios GATT espera dos segundos y publica SUCCESS. No hay
escrituras GATT, handshake Security 1, transmisión de contraseña/PoP ni lectura
del resultado del ESP32. Una torre permanece sin WiFi pese al mensaje de éxito.
Implementar protocolo oficial y exigir confirmación real. Probar SSID incorrecto,
clave incorrecta, configuración correcta y cambio de router sin reflashear.

### P1 · Falta enlace firmware 2.0 con backend/VPS

`platformio/esp32_ecogrow2/src/main.cpp:402–423` y módulo completo.
El firmware sirve rutas locales y configura WiFi; carece de cliente HTTP/MQTT,
destino backend y sincronización de lecturas/comandos. Conectarse al router no
conecta la torre con el dashboard remoto. `mobile_service.py` además conserva
TDS/litros/reportes físicos ausentes. Implementar el enlace autenticado y probar
telemetría y comando con el entorno real autorizado.

### P1 · Android remoto queda cargando tras login

`MainActivity.kt:190–195`; `EcoGrowViewModel.kt:31–44`.
Login carga towers pero no selecciona torre ni carga detail. La pantalla tampoco
presenta lista ni llama select. Con autenticación correcta permanece en Cargando;
Actualizar vuelve a listar torres. Incorporar selección y estados vacío/error.

### P1 · Bomba AUTO puede saltarse el reposo

`platformio/esp32_ecogrow2/src/main.cpp:488–505`.
Se toma ahora antes del muestreo bloqueante. El corte de encendido actualiza
timestampCiclo con un millis posterior y la resta unsigned siguiente desborda,
causando encendido inmediato en 513–515. Reproducción aritmética uint32:
ahora=600001, timestamp=600201 → elapsed=4294967096 ≥ reposo1200000.
Corregir transición temporal y probar periodos completos, corte y rollover.

### P1 · Autenticación local falla abierta

`platformio/esp32_ecogrow2/src/main.cpp:250–251`.
Usuario vacío o contraseña corta hacen authorized=true. Con la plantilla
predeterminada cualquier cliente LAN puede operar bomba/modo/receta. Exigir
configuración válida o vinculación autorizada. Android tampoco permite introducir
credenciales locales: MainActivity:214/279 invoca connectLocal sin ellas.
Resolver ambos extremos sin eliminar autenticación para conseguir conexión.

### P1 · Credenciales entran en la imagen Docker

`deploy/Dockerfile:23`; `deploy/docker-compose.yml:22`.
COPY . . usa contexto raíz sin .dockerignore. El despliegue requiere deploy/.env
antes del build: ese archivo entra en una capa de la imagen. .gitignore no filtra
Docker. Excluir secretos, config.h, datos, caches y .git del contexto o copiar solo
fuentes. Verificar con archivo centinela PRUEBA; no inspeccionar/publicar secretos.

### P1 · Comandos remotos no caducan

`services/mobile_service.py:177–180`; `Conexión/conexion.py:2216–2230,2257–2275`.
El comando manual se conserva indefinidamente y sync lo devuelve de nuevo al
reconectar. Una orden ON antigua puede ejecutarse horas después. Incorporar
identidad, vencimiento y acuse, mantener validación local, y probar desconexión
y recuperación sin reproducir una orden vencida.

## Hallazgos secundarios confirmados

- `MainActivity.kt:760–775`: campo SSID manual cuando no hay redes, pero selección
  usa selectedWifiSsid y deja el envío deshabilitado; usar el campo mostrado.
- `MainActivity.kt:370,451`: reported=null se interpreta apagado y bloquea Stop.
  Mostrar desconocido/pendiente y permitir solicitar apagado según capacidad.
- `MainActivity.kt:532`: duraciones de recetas UI difieren del firmware; mostrar
  configuración reportada. Falta seguimiento de stale/updated_at y refresco local.
- `MainActivity.kt:44–67`: lista WiFi usa caché del teléfono, no escaneo ESP32,
  y admite redes 5 GHz. Implementar escaneo vía aprovisionamiento ESP32.
- `main.cpp:388–391`: PoP constante compartida no establece posesión por torre.
  Usar mecanismo por dispositivo y recuperación física controlada.
- `scripts/deploy_vps.sh:35`: búsqueda healthy también coincide con unhealthy;
  exigir estado exacto mediante inspección estructurada.
- `.github/workflows/deploy.yml:3–6,49–54`: despliegue independiente del CI y
  git pull main móvil; condicionar a checks e imagen/commit inmutable del SHA.
- Backend /health no comprueba DB; despliegue nuevo no inicializa explícitamente
  esquema. Añadir inicialización y readiness en base de pruebas temporal.
- `blueprints/mobile.py:76–87`: límite por remote_addr detrás de Caddy agrupa
  usuarios por IP del proxy y no comparte contador entre workers. Ajustar proxy
  de confianza y limitador apropiado sin confiar cabeceras externas arbitrarias.

## Orden recomendado de corrección

1. Seguridad de firmware, temporización de bomba y exclusión de secretos Docker.
2. Aprovisionamiento BLE real y pruebas con ESP32/Android.
3. Enlace remoto con caducidad/acuse, selección de torre Android y estados honestos.
4. Deploy con checks del SHA, estado exacto, inicialización/readiness y evidencia URL.
5. Regresión Python/Android/firmware, recorrido web y prueba completa de reconexión.

El otro agente debe completar estos pasos y actualizar evidencias, sin declarar
éxito simulado ni despliegue por un workflow que saltó la ejecución. Merge y
deploy siguen las autorizaciones vigentes; esta revisión no los ejecuta.
