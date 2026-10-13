# Revisión séptima: conexión y dashboard nativo

Ámbito: ECOGROW, AISLADO. Base revisada: `d42102d580720aaed530906699d466dffc33d146`, PR #3. Revisión de código y contratos; sin ESP32 USB disponible. Se detectó un teléfono Android 12 con EcoGrow instalada; la verificación visual local se registra en la entrega de identidad.

## Resultado

La app ya contiene un dashboard Compose y un asistente de ocho pasos. No está validado el recorrido ESP32 → WiFi → dashboard. Los checks verdes de compilación no demuestran este recorrido.

## Hallazgos accionables

1. **[P1] El asistente termina abriendo una dirección que no descubrió.** `AddTowerScreen.kt:773` entrega `null` como IP. `EcoGrowViewModel.onTowerProvisioned` sustituye ese dato por `192.168.4.1`, la dirección del AP, aunque la torre acaba de ingresar al router y el móvil no se conectó a ese AP. No hay descubrimiento de IP LAN ni confirmación de `/api/status`. La pantalla anuncia comunicación con el servidor y HTTPS activo a partir de `deviceProvisioningSuccess`, que solo demuestra aprovisionamiento WiFi. Obtener/verificar la dirección real o enlazar con una torre cloud autenticada; representar WiFi confirmado y servidor pendiente por separado. Si la dirección falta, permitir recuperación explícita sin guardarla como real.

2. **[P1] Las torres guardadas no pueden reconectarse y seleccionar otra torre puede abrir la anterior.** `EcoGrowViewModel.kt:167–174` ignora `Tower.localIp` y usa el cliente `local` global o `api!!`. Después de reiniciar ambos son null: seleccionar una torre guardada falla. Con dos torres locales, seleccionar cualquiera reutiliza el último cliente. Resolver cliente por identidad seleccionada, solicitar credencial local protegida cuando corresponda, distinguir ids locales/cloud y validar selección de A/B tras reinicio. No guardar PoP en texto plano para resolverlo.

3. **[P1] La entrada cloud quedó inaccesible desde el inicio.** `MainActivity.kt:87–99` conecta Inicio únicamente a selección, añadir, conexión AP, refrescar y salir; ninguna acción abre LOGIN. La única transición actual a LOGIN es un 401, pero una instalación nueva no puede crear el cliente cloud que lo produciría. Añadir acceso visible «Iniciar sesión»/«Acceso remoto» y validar desde instalación limpia. La conexión AP además conserva una contraseña fija que no coincide con la PoP individual del firmware por defecto: pedir credencial real y dirección en ese recorrido.

4. **[P2] El dashboard lee un contrato distinto al servido y muestra estado falso.** `TowerDetailScreen.kt:35–41,55` consulta `online`, `last_seen`, `alert` y `pump.pending_command`. Backend y adaptador local suministran `stale`, `updated_at`, `alerts[]` y `pump.status/command_id`. Incluso una lectura local exitosa se dibuja sin conexión; última lectura, alertas y orden pendiente se pierden. La receta remota proporciona `crop/phase`, pero la pantalla lee `name` con Lechuga predeterminada. Usar un modelo normalizado probado con payload real local y remoto; mostrar SIN_DATO para desconocidos y respetar capacidades y lectura caducada al habilitar controles.

## Mejoras verificadas

- El escaneo de WiFi se solicita al ESP32, no al teléfono.
- Hay navegación nativa y confirmación de encendido de bomba.
- El PoP ya se oculta en la salida CLI normal y los timeouts conocidos; 19 pruebas de aprovisionamiento pasan localmente.
- CI del HEAD revisado: Android lint/unit/build, backend/MariaDB y firmware en verde. Runs 38472406030 y 38472412103.

## Pendiente de aceptación física

Instalación limpia, Bluetooth apagado, permisos rechazados, activación y regreso a la app, PoP incorrecta, WiFi incorrecta, red correcta, IP real, dashboard con lecturas, reinicio de app y torre, selección entre dos torres. El QR hoy se pega como texto; aún no existe lectura de cámara. La activación Bluetooth usa startActivity sin observar resultado/estado: validar que el paso se actualice al regresar. No presentar estas pruebas como completadas por mocks.

## Entrega de identidad visual

Los recursos de marca se incorporan en una rama separada basada en este HEAD, sin corregir silenciosamente los hallazgos del otro agente. No se realizó merge ni despliegue.
