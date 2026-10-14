# Revisión novena — servidor oculto y aprovisionamiento cloud

Ámbito ECOGROW, AISLADO. HEAD revisado `7e06310871f68891a9c2f5581613c9432a2a244b`, PR #5. Sin escritura en VPS, base real ni ESP32. Pruebas de fallos mediante mocks con identificadores PRUEBA y archivos temporales.

## Resultado

«Opciones del servidor» desapareció de LoginScreen. Se añadieron QR con code, registro dispositivos_iot, claim con hash de PoP y bloqueo de fila, NVS de identidad/token, sondeo de primera telemetría y dashboard. CI del HEAD revisado está verde; no acredita operación completa con el despliegue.

## Bloqueos accionables

1. **[P1] Aprovisionamiento devuelve éxito aunque cloud y hardware no coincidan.** tools/provision_device.py:403–420 programa un token aleatorio nuevo en cada ejecución antes de registrar DB, ignora el booleano de set_device_token y suprime toda excepción de registro. La CLI no informa db_registered y anuncia hardware verificado. Si se ejecuta nuevamente sobre una torre ya reclamada sin force, register_dispositivo_fabrica rechaza la actualización; la excepción desaparece pero NVS ya tiene otro token y la torre pierde autenticación. Si la conexión DB/import falla sucede lo mismo. Reproducción local: dos llamadas con cliente serial y DB sustituidos; status success y verified true pese a SET_TOKEN false y RuntimeError DB; tokens distintos entre ejecuciones. Conservar token existente por defecto; rotación explícita coordinada con recuperación, comprobación de token por challenge/readback sin revelarlo, registro cloud obligatorio verificado y errores seguros. No entregar etiqueta como lista cuando falta registro.

2. **[P1] El modo offline puede resetear propiedad y credenciales reales.** generate_offline_label tiene sync_db=True por defecto y llama register_dispositivo_fabrica(...,force=True), tools/provision_device.py:516–520. La función DB cambia estado a fabrica y reclamado_por a NULL y renueva hash/token. Generar un SVG para un MAC existente puede invalidar el dispositivo y borrar el reclamo sin programar hardware. El comando generate no debe acceder a DB ni alterar dispositivo por defecto; separar pruebas/offline de aprovisionamiento real y nunca forzar reset de propiedad implícitamente.

3. **[P1] La identidad por defecto aún colisiona y Android aún inventa un fallback.** getTorreCodigo devuelve el macro ECOGROW_TORRE_CODIGO (ejemplo TORRE-001); el código generado por MAC queda en una rama #else que no se usa cuando existe ese macro. La herramienta acepta ident.code antes del código por MAC y la CLI no permite desired_code, por lo que dos placas nuevas con la configuración de ejemplo pueden usar TORRE-001. Android AddTowerScreen:878–880, si no hay code de QR/entrada, conserva EG-TORRE + últimos cuatro caracteres BLE o EG-TORRE-01. La etiqueta de fábrica ahora contiene code, lo que corrige el recorrido QR bien provisionado; no corrige el recorrido manual incompleto. Exigir código canónico verificado, único y persistido; no heredar un identificador de ejemplo ni fabricar fallback operativo. Bloquear continuación o recuperar identidad autenticada cuando falte.

4. **[P1] El despliegue consultado sigue sin ruta de vinculación.** GET /health HTTPS con certifi devuelve 200; OPTIONS /api/mobile/towers/bind devuelve 404 el 2026-10-13. El backend de rama define POST y debería exponer OPTIONS. No se realizaron POST ni cambios de servidor. Preparar migración/versionado y verificar el despliegue autorizado del SHA compatible antes de acreditar operación de APK. La herramienta importa una conexión MySQL local; no demuestra que registra el inventario en la DB del Coolify autorizado. Definir y comprobar el destino de registro sin exponer credenciales ni depender de la Mac durante la operación.

5. **[P2] El token individual nuevo se filtra en errores seriales.** tools/provision_device.py:286 solo redacta SET_POP/VERIFY_POP. Un timeout de SET_DEVICE_TOKEN incluye el token completo y la CLI imprime la excepción. Reproducido con PRUEBA_TOKEN_NO_REAL_1234 y timeout=0: el mensaje contiene el valor. Redactar todos los comandos sensibles y las respuestas inesperadas, y probar stdout/stderr en éxitos y fallos. No usar argumentos de proceso para secretos.

6. **[P2] La pantalla afirma vínculo/completado aunque falle.** AddTowerScreen muestra «Configuración Completada» y «está vinculada» inmediatamente al entrar en SUCCESS, incluso mientras bind sigue pendiente o falla. Tras agotar sondeo de telemetría afirma «Transmitirá en su próximo ciclo», sin evidencia de autenticación/API correcta, y permite Entrar al Dashboard aunque falle el vínculo. Mostrar etapas reales y reintento de bind/telemetría; distinguir WiFi confirmado de dispositivo operativo. El botón actual llama onCancel y vuelve a HOME, no abre directamente el detalle de la torre vinculada.

## Mejoras verificadas y pruebas

- LoginScreen ya no contiene opción/campo de servidor; login usa DEFAULT_API_ENDPOINT.
- Persisten saved_endpoint/cliente inicial heredados de versiones previas en ViewModel: eliminar/migrar configuración obsoleta para que la sesión restaurada use el mismo destino configurado que login.
- Claim ahora requiere dispositivo registrado y PoP; hay integración MariaDB de reclamantes concurrentes en CI. No seguir reportando que code solo basta para reclamar.
- Sync reconoce token individual y rechaza identidad ajena con ese token; conserva token global para torres no registradas, compatibilidad que debe quedar explícita y acotada.
- CI 38481301390 y 38481296175: Android, backend/MariaDB y firmware verdes en HEAD 7e06310.
- Local: 37 test_mobile, 19 test_provision_device correctos; git diff --check limpio. Las pruebas de aprovisionamiento aún pasan a pesar de los fallos reproducidos: ampliar casos de registro fallido, token persistido, respuesta negativa, segundo aprovisionamiento y modo offline sin escritura.

## Aceptación pendiente

Corregir estos bloqueos juntos. Luego, dispositivo de fábrica registrado en el destino correcto, identidad/PoP/token coherentes, WiFi, claim, primera telemetría, comandos desde datos móviles, ACK físico, reinicios y dos torres aisladas. No se ejecutó esta aceptación física ni merge/deploy en la revisión.
