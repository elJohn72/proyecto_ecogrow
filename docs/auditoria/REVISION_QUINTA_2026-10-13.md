# Quinta revisión EcoGrow — PR #3, HEAD f7f7ae9

Fecha: 2026-10-13. Ámbito ECOGROW, AISLADO. Revisión sin escrituras sobre
hardware, servidor o datos del laboratorio; no se generan ni publican PIN reales.

## Correcciones verificadas

- Sync persiste el reporte físico de bomba también en manual.
- El adaptador ya no utiliza el ACK de una orden ejecutada como reporte físico.
- Reconfiguración WiFi conserva la PoP y se separa del factory reset.
- Se añadió servicio MariaDB en CI y pruebas con procesos independientes.
- Log de CI del HEAD revisado, run 38432395952: 56 pruebas ejecutadas, OK,
  incluyendo rollback, concurrencia, expiración, aislamiento y ciclo multiworker.
- Los checks Android y firmware del mismo HEAD también están verdes.

Los dos últimos frentes de reporte de bomba y validación SQL están mejorados
y tienen evidencia. Permanece el bloqueo de vinculación de identidad de fábrica.

## P1 · El PIN de la etiqueta no se instala ni verifica en el ESP32

`tools/provision_device.py:108–123,141–147` genera un PIN aleatorio en el ordenador
y escribe únicamente una etiqueta SVG. No se comunica con el ESP32 ni produce
una partición NVS, escribe `ecogrow/pop`, entrega configuración al firmware o
verifica un valor previamente provisionado.

`platformio/esp32_ecogrow2/src/main.cpp:588–600` genera otra PoP independientemente
si NVS no contiene una. Ninguna ruta enlaza la herramienta de fabricación con
esa PoP. Por tanto el procedimiento documentado `generate --mac ...` no instala
el PIN impreso y el equipo nuevo no puede autenticarse con su etiqueta.
La opción --pop permite escribir un valor en papel, pero no resuelve su carga
en NVS ni la recuperación del valor aleatorio ya creado por la torre.

Corrección requerida: implementar un único flujo de fabricación que genere
el secreto una sola vez y lo instale en la identidad del ESP32 antes de operar,
o un mecanismo físico autorizado que obtenga de forma segura la identidad
provisionada y genere su etiqueta. Verificar coincidencia y autenticación real
antes de entregar el equipo. No introducir una contraseña global, no publicar
el secreto por HTTP/BLE sin autenticación ni volcarlo en logs generales.

Entregar herramienta y runbook completos (NVS/puerto/dispositivo y readback
seguro), manejo de fallos y recuperación. La etiqueta debe corresponder al
equipo real y conservarse al cambiar de router; factory reset requiere un nuevo
aprovisionamiento de fábrica documentado.

## Precisión documental y prueba física

La herramienta anuncia QR, pero el SVG revisado solo tiene textos y elementos
de la etiqueta; no codifica el payload en un QR escaneable. Implementar QR real
si se promete, o documentar únicamente entrada manual del PIN.

No se comprobó onboarding con ESP32 y teléfono físicos en esta revisión.
CI verde y tests SQL no acreditan coincidencia PoP etiqueta/firmware ni Security 1.
Resolver el bloqueo de fabricación y aportar prueba de equipo nuevo y cambio
de WiFi antes de declarar la entrega completa. No se fusionó ni desplegó el PR.
