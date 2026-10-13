# Revisión octava — cliente remoto y vinculación ESP32

Ámbito ECOGROW, AISLADO. HEAD revisado: `11f4725b48706a799063a8f85364559504384155`, PR #5 (base main), incluye trabajo PR #3 y #4. Revisión de código, pruebas locales y consultas HTTP de lectura; sin órdenes al hardware ni modificaciones del VPS.

## Dictamen

No está listo para aprobar como aplicación completamente funcional. Android ya consume la API remota y elimina LocalTowerApi y la acción «Probar en red local». Login inicial, modelos tipados, alertas y QR con cámara están implementados. Quedan bloqueos de identidad, posesión y despliegue.

## Hallazgos

### [P1] Android vincula un código distinto al que reporta la ESP32

`android/app/src/main/java/com/ecogrow/mobile/AddTowerScreen.kt:845` fabrica `EG-` + últimos cuatro caracteres del nombre BLE. El QR solo aporta nombre BLE/PoP/transporte y su lector conserva el PoP; no hay identidad cloud autenticada recuperada del hardware. `platformio/esp32_ecogrow2/src/main.cpp:418` reporta el macro ECOGROW_TORRE_CODIGO, cuyo valor de ejemplo es TORRE-001. Configurar WiFi no cambia ese macro ni transmite el código elegido por Android. La fila creada por la app puede no recibir jamás lecturas ni comandos de esa ESP32. Los cuatro caracteres también pueden colisionar.

Corregir con una identidad única canónica del dispositivo, registrada/verificada por el backend y compartida con firmware y etiqueta; no derivar identidad operativa de un nombre anunciado ni fabricar un código cuando falta el dato. Validar dos dispositivos reales con códigos distintos.

### [P1] La vinculación no verifica posesión y permite reclamar códigos sin dispositivo

`blueprints/mobile.py` acepta code/name/location; `services/mobile_service.py:284–306` llama a register_torre sin desafío, prueba PoP, secreto de reclamo ni verificación de existencia del dispositivo. `Conexión/conexion.py:1611` únicamente impide reclamar un código ya asignado a otra cuenta; crea cualquier código nuevo a quien lo solicite primero. El control del asistente en Android no protege una API que puede llamarse directamente. No es suficiente que el solicitante haya iniciado sesión.

Reproducción local sin datos reales ni escrituras: bind_tower(999, PRUEBA-SIN-DISPOSITIVO, PRUEBA, PRUEBA), register/fetch sustituidos por mocks, devuelve éxito sin prueba del dispositivo. Las pruebas nuevas sustituyen bind_tower/register_torre, por lo que no acreditan posesión ni concurrencia real.

Implementar registro de dispositivo y reclamo de posesión autenticado, atómico, con expiración/replay y propiedad. Pruebas reales MariaDB: sin prueba, incorrecta, expirada, repetida, dos reclamantes simultáneos y acceso/control cruzado. La credencial cloud del dispositivo debe autorizar únicamente su identidad; actualmente `/api/iot/sync` sigue usando un SENSOR_API_TOKEN compartido y acepta torre_codigo del payload.

### [P1] La API desplegada aún no tiene la ruta que necesita la app

Consulta HTTPS con validación TLS (certifi), 2026-10-13:
- GET /health → 200, status ok, database connected.
- GET /api/mobile/session → 200, authenticated false.
- OPTIONS /api/mobile/towers/bind → 404.

El código local define POST en esa ruta y Flask permite OPTIONS; el despliegue consultado no la expone. No se probó POST porque generaría escritura y no es necesario para demostrar esta incompatibilidad. El APK no puede dar por disponible una funcionalidad por existir en la rama. Tras corregir y obtener autorización de merge/deploy, verificar el SHA desplegado, migraciones y rutas. Sin editar código manualmente en el VPS.

### [P1] Falta completar el aprovisionamiento de identidad/credencial cloud del dispositivo

`main.cpp:382` lee api_token de NVS o ECOGROW_SENSOR_API_TOKEN; sin token válido omite sincronización. No se encuentra ningún escritor de api_token en firmware ni en el protocolo de taller; herramientas programan PoP y el asistente configura únicamente WiFi. Una build con config.h privado podría incluir credencial, pero no hay evidencia de cuál está en el hardware ni de su correspondencia con la API. No afirmar que todos los dispositivos se conectarán por terminar WiFi.

Completar un procedimiento seguro de fábrica o un canal de aprovisionamiento autenticado, con credencial individual, identidad persistida y recuperación WiFi que la conserve. No distribuir el token global administrativo a Android. Verificar comunicación del dispositivo y primera telemetría antes de habilitar la torre como operativa.

## Verificaciones y límites

- CI de HEAD 11f4725: backend/MariaDB, Android lint/unit/build y firmware verdes en runs 38477136203 y 38477079027.
- Local: 35 test_mobile correctos; git diff --check limpio.
- Corregidos: dependencia de LAN en Android, entrada de login, selección por ID cloud y normalización de campos principales del dashboard.
- El paso final ya distingue WiFi y registro cloud, pero solo anuncia que la telemetría comenzará: no consulta hasta confirmar la primera lectura. Añadir estado pendiente y confirmación real.
- No se introdujeron credenciales, datos reales ficticios, comandos de bomba, merge ni deploy.
- Prueba física pendiente: dispositivo registrado → PoP/BLE → WiFi → reclamo probado → primera lectura → control desde datos móviles → ACK físico → reinicios y dos torres aisladas.

## Entrega al implementador

Resolver juntos los cuatro bloqueos, conservar la identidad visual y el cliente remoto; no añadir de nuevo acceso LAN. No presentar mocks/compilación como prueba de operación física. La aprobación del producto exige evidencia del recorrido completo y compatibilidad con el despliegue autorizado.
