# Sexta revisión EcoGrow — PR #3, HEAD b764d0d

Fecha 2026-10-13. Ámbito ECOGROW, AISLADO. Revisión sin operar hardware ni
modificar código funcional/servidor. No se utiliza ni publica ningún PIN real.

## Vínculo de identidad corregido en software

La herramienta provision consulta identidad mediante UART, conserva PoP existente
por defecto o la instala con SET_POP, verifica con VERIFY_POP y emite etiqueta
solo si hay coincidencia. Firmware implementa los handlers correspondientes.
La etiqueta SVG incluye una matriz QR codificada por qrcode; dejó de ser solo
un texto. Hay pruebas de conservación, instalación, verificación fallida y archivos.
Cambiar WiFi conserva identidad; factory reset se mantiene separado.

## Evidencia

- CI del HEAD b764d0d, run 38461907121: 72 pruebas Python unitarias/integración,
  OK, con MariaDB y múltiples procesos. No aparecen saltos en ese resumen.
- Checks Android y firmware del mismo HEAD verdes.
- Dependencias locales actualizadas desde requirements.txt; las 16 pruebas
  test_provision_device pasan localmente.
- git diff --check sin incidencias; checkout limpio antes de guardar este reporte.

No se conectó ESP32 ni teléfono. Los tests de protocolo serie usan mocks;
no acreditan la autenticación BLE física, escaneo del QR impreso ni recuperación
del router en una torre. Mantener estas evidencias como PENDIENTE_FISICO.

## P2 · PIN expuesto en errores y salida normal de la herramienta

`tools/provision_device.py:249,323,457,462–463`.
El timeout de send_command incluye cmd completo, que para SET_POP/VERIFY_POP
contiene la PoP. La discrepancia de readback incluye target_pop. El CLI imprime
esas excepciones en stderr y también imprime el PIN en su salida de éxito/read.
Una ejecución capturada en logs de agente/taller puede divulgar la credencial.

Reproducción local sin hardware y con token explícitamente PRUEBA: el puerto
simulado agota timeout y la excepción contiene el PIN de prueba. No se usó ni
mostró una credencial real.

Corrección: mensajes deben identificar la operación y el equipo sin incluir
argumentos sensibles, respuestas seriales con PoP ni target_pop. Salida normal
debe mostrar solo estado y ruta del archivo protegido. La entrega física del
PIN ocurre en la etiqueta/canal de taller autorizado, sin volcarlo en logs.
Añadir tests de captura stdout/stderr para éxito, timeout, error de readback y
respuesta inesperada; verificar que nunca contienen PoP. Revisar también opciones
CLI con PoP en argumentos y ofrecer lectura protegida sin exposición por ps.

## Cierre

El bloqueo funcional etiqueta/ESP32 está resuelto a nivel de código y mocks.
Queda el ajuste P2 de confidencialidad y la prueba física acordada. Actualizar
el PR/HEAD y volver a comprobar checks tras corregirlo. Esta revisión no fusiona,
no despliega ni declara que la torre física esté validada.
