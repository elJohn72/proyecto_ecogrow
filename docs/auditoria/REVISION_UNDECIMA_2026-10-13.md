# Revisión undécima — migración y recuperación de aprovisionamiento

Ámbito ECOGROW, AISLADO. HEAD revisado `f31b3ca0ef2c47d4f33d2a06196b405f9c0fe036`, PR #6. No se modificó VPS, hardware ni DB real. Consultas HTTPS de lectura, análisis de esquema, pruebas y reproducciones PRUEBA con mocks.

## Resultado

Correcciones verificadas: preflight de propiedad antes de SET, comprobación VERIFY_DEVICE_TOKEN, conservación offline del token, error DB explícito y estado operativa condicionado a primera telemetría. Persisten errores de migración y recuperación; el despliegue compatible sigue pendiente.

## Hallazgos accionables

1. **[P1] La migración real ejecuta SQL contra una columna inexistente.** tools/migrate_identities.py usa `UPDATE torres SET codigo_torre = %s WHERE codigo_torre = %s`. El schema real en Conexión/conexion.py define `torres.codigo_unico`; codigo_torre pertenece a dispositivos_iot. Al aplicar una migración, MariaDB rechazará el UPDATE y se revertirá la transacción. Las cinco pruebas pasan porque sustituyen conexión/cursor por MagicMock; incluso la prueba llamada real no ejecuta SQL real. Corregir columna, comprobar conflictos tanto en inventario como en torres y añadir integración con MariaDB temporal que ejecute migración, preserve usuario/id/historial y pruebe segundo intento idempotente. Reproducción auxiliar SQLite en memoria con la columna real confirma que el SQL no referencia un campo del esquema; no se presenta como integración MariaDB.

2. **[P1] Recuperación parcial y no verificada tras error.** tools/provision_device.py restaura solo token cuando falla registro DB; no restaura PoP ni código modificados. La devolución false de set_device_token durante rollback se ignora y no hay VERIFY posterior. Errores de restauración se suprimen. Si falla el readback del token justo después de SET, aún no se marcó token_written y tampoco entra en recuperación DB. No hay estado persistente para recuperar una interrupción del proceso. Reproducción con mocks: desired_pop cambia PoP, DB falla, rollback del token devuelve false; PoP se escribió una vez sin restauración y no hubo readback tras rollback. Completar un protocolo recuperable e idempotente para todas las mutaciones y fallos, incluidos serial/readback/interrupción. Si no puede restaurarse, registrar de manera protegida un estado de reparación verificable; no silenciarlo ni anunciar identidad conservada.

3. **[P1] La lectura/migración del firmware modifica identidad sin coordinación cloud.** getTorreCodigo detecta placeholder en NVS y guarda automáticamente otro código. ECOGROW:IDENT? llama esa función, por lo que el supuesto preflight de solo lectura puede mutar hardware antes de comprobar propietario/cloud. La migración DB es independiente del cambio del ESP32 y la etiqueta. Una torre vinculada puede cambiar lo que reporta antes de actualizar el registro remoto. Separar lectura de identidad de migración, y coordinar identidad/propiedad/etiqueta con un procedimiento de actualización seguro y recuperable. No cambiar una identidad activa solo en un extremo por arrancar o consultar IDENT.

## Pendiente de despliegue, reconocido por el implementador

Consulta TLS validado con certifi el 2026-10-13: GET /health 200; OPTIONS /api/mobile/register y /api/mobile/towers/bind 404. docs/despliegue/ESTADO_DESPLIEGUE_COOLIFY.md reconoce explícitamente que hace falta merge/deploy autorizado. No es una corrección desplegada. No afirmar funcionamiento completo del APK contra el VPS hasta comprobar versión compatible, migraciones y flujo real. En ese documento, retirar curl -k (omisión de validación TLS) y corregir descripción bcrypt: el registro usa el hash seguro de Werkzeug, no bcrypt según el código actual.

## Evidencia de validación

CI 38498834685 y 38498830669 en HEAD f31b3ca: backend/MariaDB, Android y firmware verdes. Local: 41 test_mobile, 29 test_provision_device y 5 test_migrate_identities correctos; git diff --check limpio. Estas pruebas todavía no cubren migración SQL real ni restauración completa.

No se realizó aceptación física. Tras corregir: registro/login remotos, torre con código/QR/PoP/token coherentes, primera lectura, control desde datos móviles, ACK físico, reinicios y dos torres/usuarios sin cruces. Sin merge/deploy ni órdenes de bomba durante esta revisión.
