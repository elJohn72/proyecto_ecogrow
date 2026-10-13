# Cuarta revisión EcoGrow — PR #3 actualizado

Fecha 2026-10-13. Ámbito ECOGROW, AISLADO. HEAD `e70a26a`.
Sin cambios funcionales, operación de hardware ni escrituras sobre el VPS/DB.

## Evidencia y correcciones

- 48 unittest Python ejecutadas localmente: OK.
- CI del HEAD e70a26a: success en backend/web, Android y firmware.
- ACK SQL incluye torre_id y estado pendiente; se eliminó wildcard sin ID.
- Persistencia ya no cae a diccionario en memoria; errores generan 503 y
  superseder/insertar usan una transacción con rollback.
- Se consulta el último comando de bomba separado de modo/receta.
- Volumen inferido requiere deposito_calibrado; capability respeta esa condición.
- PoP nueva utiliza aleatoriedad y se persiste, sin imprimirla en Serial.

Resultado: mejoras confirmadas, pero NO LISTO COMO ENTREGA COMPLETA por los
dos escenarios siguientes y la validación física/SQL aún pendiente.

## P1 · PIN aleatorio no tiene mecanismo de entrega/recuperación

`platformio/esp32_ecogrow2/src/main.cpp:588–600`.
En equipo nuevo se genera la PoP dentro del ESP32 y se escribe solo en NVS.
Android requiere introducirla desde una supuesta etiqueta, pero no se implementa
proceso para provisionar esa etiqueta/QR ni canal físico autorizado que entregue
el secreto. El código, docs y herramientas revisados no completan ese paso.
La ruta administrativa exige esa misma PoP: no puede usarse para descubrirla
sin autenticación previa. Tras BOOT, prefs.clear en :644 borra la PoP y genera
otra, por lo que una etiqueta anterior tampoco sirve después de recuperación.

Completar el onboarding seguro: PoP provisionada por dispositivo y etiqueta/QR
mediante herramienta de fabricación, o mecanismo de entrega física autorizado
explícito. Separar reinicio WiFi de borrado de identidad/PoP para conservar el
canal de recuperación acordado. No imprimir secretos en logs generales ni
reintroducir valores públicos/compartidos. Probar equipo nuevo y cambio de router.

## P1 · Estado físico de bomba sigue descartándose en manual

`Conexión/conexion.py:2324–2341`; `services/mobile_service.py:389–402`.
sync_iot_device solo almacena rele_principal_on si modo != manual. Las órdenes
de la app ponen modo manual, precisamente el caso en que deben conservarse
los reportes físicos posteriores. Después de ON ejecutado, botón físico OFF o
límite de tiempo, el ESP32 reporta apagado pero backend lo ignora. tower_detail
puede seguir mostrando ON a partir del ACK histórico o de un reporte anterior.

Reproducción local con mocks, sin DB: sync en manual recibe
rele_principal_on=False; set_actuador_estado no se llama (reporte_persistido=False).
Separar estado deseado del reportado para no borrar una orden al recibir
telemetría; persistir siempre el reporte físico con fecha y origen. El ACK de
una ejecución anterior no es una lectura actual. Validar ON → ACK → apagado
físico/por timeout → sync OFF → ambas interfaces OFF, sin enviar otro comando.

## Comprobaciones aún no acreditadas

`tests/test_mobile.py:test_persistent_command_sharing_across_workers` usa un
diccionario simulado y llamadas secuenciales en el mismo proceso. No prueba
MariaDB, transacciones/restricciones reales ni varios workers concurrentes.
La transacción implementada mejora la atomicidad, pero la corrección también
requiere un gate de integración con DB temporal para rollback, concurrencia y
orden de comandos. No tocar datos del laboratorio para fabricar esa evidencia.

Falta prueba física del onboarding BLE y recuperación de la torre. Mantener
esas verificaciones pendientes hasta disponer de banco autorizado; CI verde no
las sustituye. Resolver los dos hallazgos, completar evidencia y revisar HEAD
final antes de solicitar merge o declarar entrega integral.
