# Segunda revisión EcoGrow: Coolify y correcciones full-stack

Fecha: 2026-10-13. Ámbito ECOGROW, AISLADO. Revisión sin parches funcionales,
sin credenciales publicadas, sin operación de hardware ni cambios en el VPS.
Código inicial revisado `67d4520`; comprobación posterior del merge `5d00113`.
La diferencia intermedia es documentación y no corrige los puntos siguientes.

## Resultado

NO LISTO COMO ENTREGA INTEGRAL. PR #2 fusionado durante la revisión.
Los checks de su HEAD `9696e79` pasan, pero no comprueban los flujos físicos ni
la entrega de comandos entre workers. No inferir una validación física por compilación.

## Mejoras confirmadas

- Backend en Coolify responde HTTP 200 en /health, con database connected.
- /control anónimo redirige a /login; la ruta del dashboard existe.
- Docker ahora copia explícitamente fuentes y tiene .dockerignore.
- Android incluye el SDK Espressif y eliminó la espera de éxito simulado.
- Hay cliente de sincronización en firmware y estructura de comandos TTL/ACK.
- Se corrigió la selección de torre Android y se reorganizó la temporización.
- CI pasa en Python/web, Android y compilación/test C++ de firmware.

## P1: BLE inicia aprovisionamiento antes de terminar conexión

`android/app/src/main/java/com/ecogrow/mobile/BleProvisioningManager.kt:157–160`.
connectBLEDevice inicia conexión GATT asíncrona y se llama inmediatamente
provision sin esperar conexión y descubrimiento de características del SDK.
La revisión de la biblioteca 2.4.4 muestra que la sesión utiliza características
descubiertas: antes de completarlas falla el transporte. Esperar evento oficial
de conexión/discovery, inicializar Security 1 y después aprovisionar. Probar con
ESP32 real, clave incorrecta y reconexión; no restaurar el éxito simulado.

## P1: órdenes y ACK aislados por proceso

`services/mobile_service.py:22,37,42,51`; `Dockerfile:46`.
_pending_commands es diccionario en memoria; Gunicorn arranca tres workers.
POST, sync y consulta/ACK pueden ejecutarse en procesos diferentes, sin compartir
comandos. También se pierden al reiniciar. Reproducción local sin DB, usando dos
procesos independientes: creador_tiene_orden=True; worker_sync_tiene_orden=False.
Usar almacenamiento compartido persistente con estados/TTL/ACK y pruebas reales
de múltiples workers. No resolverlo ocultando el problema con mocks de un proceso.

## P1: HTTPS no está operativo y firmware no lo soporta

Endpoint verificado:
`w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io`.
/health funciona por HTTP. La misma petición HTTPS con validación normal falla
por certificado autofirmado. No se omitió validación ni se aceptó excepción.
`platformio/esp32_ecogrow2/src/main.cpp:344–348` utiliza WiFiClient sin TLS.
Configurar certificado confiable en Coolify y cliente seguro del ESP32 con
validación adecuada; publicar el endpoint HTTPS correcto en Android. No usar
setInsecure ni permitir HTTP remoto para dar por solucionado el flujo.

## P1: credenciales compartidas/incorporadas

`platformio/esp32_ecogrow2/src/main.cpp:116–123,265–277,521`.
Se mantienen valores comunes de PoP/autenticación y token por defecto incorporado
en código versionado. No se reproducen sus valores aquí. La vinculación debe
demostrar posesión por dispositivo; un valor público común no lo acredita.
Eliminar secretos del código/APK, usar identidad y credenciales por dispositivo,
fallar cerrado y evaluar rotación de cualquier valor que haya sido utilizado.
No se autenticó contra el entorno con ese token ni se inspeccionaron secretos.

## P1: TDS y litros no completan la ingesta

`platformio/esp32_ecogrow2/src/main.cpp:362`; `blueprints/sensores.py:276–286`;
`services/mobile_service.py:154–164`.
Firmware envía tds_ppm, pero la ruta sync no lo pasa al almacenamiento, cuyo
esquema no contiene esa medición ni litros. El adaptador los busca y activa
capacidades sin implementar el flujo real; permanecen ausentes. Añadir contrato,
esquema/migración temporal probada e ingesta, diferenciando EC, TDS y volumen
calibrado. Verificar lecturas persistidas y visibles en ambos clientes.

## P2: controles remotos de modo/receta llaman cliente local nulo

`EcoGrowViewModel.kt:64–65`; controles de `MainActivity.kt:520–530,590–605`.
En sesión remota local es null. La UI ofrece acciones que utilizan local!! y
fallan sin enviar ninguna petición remota. Respetar capabilities o implementar
comandos remotos completos, incluyendo estados solicitados/reportados.

## P2: apagar remoto no sale de AUTO

`platformio/esp32_ecogrow2/src/main.cpp:404–408`.
PUMP_OFF apaga y confirma, pero no cambia modo a manual como PUMP_ON. Si estaba
en AUTO la torre reenciende al terminar el reposo, mientras backend interpreta
orden manual. Definir parada temporal o detener en manual; reflejar intención
y estado real en interfaz y probar la transición.

## Verificaciones pendientes y siguiente entrega

Corregir estos puntos en rama/PR y validar HEAD final. Luego comprobar certificado,
aprovisionamiento físico, telemetría completa, órdenes entre varios workers,
ACK/expiración/reinicio y parada remota en AUTO. Mantener protección administrativa
del laboratorio; no reabrir 8000 público ni SSH por contraseña.

La salud del servidor y los respaldos SSH/Coolify ya resueltos no sustituyen
pruebas funcionales de EcoGrow. Este reporte no declara merge listo ni despliega.
