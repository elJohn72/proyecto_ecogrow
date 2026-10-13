# Tercera revisión EcoGrow — PR #3

Fecha: 2026-10-13. Ámbito ECOGROW, AISLADO. HEAD revisado `31d543a`.
Revisión sin modificar código funcional, servidor ni hardware. No se publican
credenciales ni se ejecutan escrituras sobre la base de datos del laboratorio.

## Resultado

NO LISTO PARA MERGE: permanecen fallos de autorización y consistencia. Los 43
unittest pasan; CI del HEAD también pasa en backend/web, Android y firmware.
Los escenarios siguientes no están cubiertos por esas comprobaciones.

## Correcciones observadas

- BLE ahora espera EVENT_DEVICE_CONNECTED antes de llamar provision del SDK.
- Existe persistencia SQL de comandos y columnas para TDS/volumen.
- Firmware incluye WiFiClientSecure, raíz ISRG Root X1 y sincronización horaria.
- HTTPS /health responde 200, database connected, verificado con certifi y con
  la raíz del firmware. La validación inicial usando el almacén local de Python
  falló por su cadena de confianza: no atribuir ese fallo al servidor.
- Se añadieron endpoints remotos de modo y receta y parada manual de bomba.
- Todavía falta evidencia de prueba física BLE/ESP32 y recorrido de multiworker
  con base temporal real, incluyendo las condiciones adversas de este reporte.

## P1 · PoP y contraseña administrativa deducibles del anuncio BLE

`platformio/esp32_ecogrow2/src/main.cpp:582,584–594,308–309`.
El nombre anunciado contiene los últimos dos bytes MAC. La PoP predeterminada
se construye con esos mismos bytes y un prefijo fijo. Cualquiera que vea el
anuncio puede calcularla. Esa PoP también es contraseña HTTP de respaldo, y se
imprime en Serial. Es identificador público, no prueba secreta de posesión.
Generar secreto aleatorio por dispositivo, persistirlo y entregarlo mediante
canal físico autorizado. No derivarlo de datos anunciados ni imprimirlo en logs.
El usuario debe poder configurar WiFi sin una contraseña global/publicable.

## P1 · ACK SQL no comprueba torre propietaria

`services/mobile_service.py:176–180`.
UPDATE cuando hay cmd_id filtra solo id_comando y omite torre_id. El parámetro
torre_id de la sincronización no protege la actualización. Un ACK con ID de
otro equipo puede marcar su orden executed/rejected y falsear la actuación.
Reproducción con _execute simulado: WHERE no contiene torre_id y los argumentos
no incluyen la torre. Añadir comprobación de torre/dispositivo, estados y ACK
válidos, rechazar IDs ajenos y probar con dos torres.

## P1 · Persistencia fallida se acepta y cae a memoria local

`services/mobile_service.py:39–52,90–102,129–161`.
Los creadores guardan en _pending_commands antes de SQL y ocultan excepciones.
Si el INSERT falla, devuelven pending; lectura usa el diccionario como fallback.
El problema entre workers vuelve cuando tabla no existe, migración falla o DB
no está disponible. Reproducción sin DB: _execute lanza una excepción y aún
create_pump_command devuelve pending/get_active_command encuentra orden local.
Usar DB como única fuente de verdad y devolver error si no se persiste.
Superseder e insertar en transacción, sin invalidar una orden anterior si falla
la nueva. Validar error de INSERT y concurrencia con varios workers.

## P2 · Estado bomba se calcula a partir de cualquier clase de comando

`services/mobile_service.py:324–343`.
Cuando el último comando se ejecuta, reported recibe active_cmd.desired incluso
si acción es SET_MODE o SET_RECIPE: resulta AUTO/MANUAL o un número en un campo
que debe ser on/off. Ambos clientes dejan de reflejar el estado físico. Mantener
reporte de bomba separado del acuse y del estado deseado de modo/receta.
Prueba: cambiar receta/mode después de encender y verificar estado independiente.

## P2 · Volumen inferido con capacidad por defecto no calibrada

`Conexión/conexion.py:2271–2277`, default en `:71` y esquema `:398`.
Cuando no llega volumen, el backend calcula litros con deposito_litros, cuyo
valor por defecto es 5 L. No existe verificación de geometría/calibración.
Así una torre sin volumen medido obtiene una cifra presentada como real.
Requerir evidencia/configuración explícita de calibración y fuente; mantener
NULL/SIN_DATO para equipos antiguos/no calibrados, sin inferir desde un default.

## Pendientes del cierre

Además de estos hallazgos, revisar atomicidad y orden determinista de comandos:
se ordenan solo por creado_en (segundos) y las escrituras usan conexiones separadas.
No basta que cada INSERT funcione para demostrar semántica con concurrencia.

El otro agente debe corregir los puntos en el PR, ejecutar pruebas de regresión
y de escenarios adversos, y validar checks del HEAD final antes de solicitar
merge. Conservar acceso administrativo protegido del laboratorio, secretos fuera
de git y alcance de las autorizaciones previas. Esta revisión no fusiona ni despliega.
