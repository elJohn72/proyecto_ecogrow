# Verificación décima — registro y resolución de auditoría novena

Ámbito ECOGROW, AISLADO. HEAD revisado `07bf89dbe3344ac97288a926af97d5525aef1d22`, PR #6, base main tras merge de PR #5. Consultas HTTPS de lectura y reproducciones con mocks; sin usuarios nuevos reales, DB real, órdenes de bomba ni modificación de VPS/hardware.

## Resultado

Registro nativo implementado con nombre/correo/contraseña/confirmación, API de registro, hash seguro y sesión automática. Login sin opciones de servidor ni LAN. No acreditar funcionamiento completo todavía.

## Hallazgos pendientes

1. **[P1] Despliegue incompatible con registro y vinculación.** El 2026-10-13, GET /health devuelve 200; OPTIONS de /api/mobile/register y /api/mobile/towers/bind devuelve 404. La rama define ambas rutas POST. Completar merge/deploy autorizado, migraciones y verificación del SHA y rutas compatibles antes de entregar como funcional contra el VPS. No se ejecutaron POST de registro ni bind en el servidor.

2. **[P1] Aprovisionamiento aún muta hardware antes de terminar preflight y puede dejar token inconsistente.** tools/provision_device.py:385–408 cambia PoP/código antes de comprobar si el dispositivo ya está reclamado (412–417). Una llamada con desired_pop sobre dispositivo reclamado escribe PoP y luego rechaza la operación sin restaurarlo. Rotación explícita escribe token antes de register_dispositivo_fabrica; si esa DB falla, se propaga error pero el hardware queda con un token que cloud no reconoce. Con sync_db=False y has_token=True, al no tener registro DB genera/escribe un token nuevo pese a no solicitar rotación. Además la conservación desde DB confía en has_token y no verifica que el valor físico corresponda al token guardado.

Reproducciones locales con mocks y directorio temporal: (a) PoP y código escritos antes de ValueError por dispositivo reclamado; (b) SET_TOKEN llamado una vez antes de error DB sin restauración; (c) no-db modifica token existente y devuelve verified=True sin rotate_token. Sin hardware/credenciales reales.

Corregir preflight completo antes de mutación; lectura/verificación autenticada de identidad/token sin revelar secretos; conservar de verdad al reimprimir/verificar; separar offline de programación. Rotación con estados persistentes y recuperación coordinada, no basta con evitar la etiqueta. Pruebas de caída/interrupción y reintento desde cada etapa.

3. **[P2] El encabezado aún declara operativa una torre sin telemetría.** AddTowerScreen elige «Torre Vinculada y Operativa» basándose solo en cloudBindSuccess, antes de telemetryConfirmed, incluso tras timeout. El registro y la vinculación no prueban autenticación del dispositivo ni disponibilidad de sensores. Hacer depender operativo de primera lectura verificada; mostrar «Vinculada · esperando datos» y recuperación cuando no llegan lecturas. No incluir Coolify/código interno en explicaciones del operador.

4. **[P2] Persistencia de códigos antiguos de ejemplo.** getTorreCodigo valida el macro de ejemplo, pero retorna inmediatamente cualquier torre_code NVS de longitud >=3. Una placa programada previamente con TORRE-001 conserva ese código si solo se actualiza firmware; necesita migración segura e idempotente que respete dispositivos reales vinculados. La herramienta ahora filtra algunos placeholders al ejecutarse; no es una migración automática de hardware ya existente. Registrar qué actualización/taller requiere el parque instalado.

## Mejoras que sí están verificadas

- Registro/login nativos y eliminación/migración de saved_endpoint.
- Android exige código de etiqueta/QR, sin fallback fabricado por sufijo BLE.
- Generación offline ya no escribe DB por defecto; force explícito.
- SET_TOKEN false ahora aborta; error DB se propaga y no genera etiqueta de éxito.
- Timeout de SET_DEVICE_TOKEN redactado.
- Estados de error de bind y reintento; botón final abre detalle por ID.
- CI del HEAD revisado: Android lint/unit/build, backend/MariaDB y firmware verdes en runs 38495744641 y 38495723541. Local: 41 test_mobile y 25 test_provision_device correctos; git diff --check limpio.

## Aceptación pendiente

Registro contra API desplegada compatible → torre con etiqueta/código/PoP/credencial coherentes → WiFi BLE → claim → primera lectura → control desde datos móviles → confirmación física → reinicios y dos usuarios/torres aislados. No se realizó esta aceptación física ni merge/deploy durante la verificación.
