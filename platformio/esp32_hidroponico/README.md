# Nodo ESP32 para EcoGrow

Proyecto base de PlatformIO para enviar lecturas del sistema hidroponico a Flask.

## Flujo

1. El ESP32 se conecta a la red WiFi.
2. Lee sensores del sistema.
3. Envia un `POST` en JSON a `http://IP_PC:5001/api/sensores/lectura`.
4. Flask identifica la torre por su codigo unico, toma el cultivo activo de esa fase y guarda la lectura en MySQL.

## Archivos importantes

- `platformio.ini`: configuracion del proyecto.
- `include/config.h.example`: ejemplo de configuracion local.
- `src/main.cpp`: firmware base para envio de datos.

## Antes de compilar

1. Copia `include/config.h.example` como `include/config.h`.
2. Ajusta:
   - SSID de WiFi
   - clave WiFi
   - IP local de tu computador
   - identificador del dispositivo
   - `TORRE_CODIGO` de la torre registrada en EcoGrow

## Sensores sugeridos para integrar despues

- DHT22 para temperatura y humedad del aire
- DS18B20 para temperatura del agua
- sensor de pH
- sensor TDS o EC
- sensor de nivel de agua
- BH1750 o LDR para luminosidad

## Observacion

El `main.cpp` usa funciones simuladas para las lecturas. Eso te permite validar primero la comunicacion HTTP con Flask y luego reemplazar esas funciones por la lectura real de cada sensor.

## Flujo recomendado

1. Inicia sesion en EcoGrow.
2. Registra tu torre con su codigo unico.
3. Elige el cultivo activo de esa torre para la fase actual.
4. Coloca ese codigo en `TORRE_CODIGO`.
5. Compila y sube el firmware al ESP32.
