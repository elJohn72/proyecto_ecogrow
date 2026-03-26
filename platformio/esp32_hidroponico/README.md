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

## Sensores y arquitectura objetivo

- `Analog pH V1.0 (DFRobot)` para pH
- `TDS Meter V1.0 (DFRobot)` para EC/TDS
- `DS18B20 waterproof` para temperatura del agua
- `TOF10120` para nivel o profundidad del deposito
- sensor ambiental para temperatura y humedad del aire
- BH1750 o LDR para luminosidad

## Secuencia recomendada de muestreo

1. Desenergizar el nodo EC.
2. Esperar ventana de estabilizacion del pH.
3. Leer pH con la referencia limpia.
4. Reenergizar EC.
5. Esperar estabilizacion corta y leer EC/TDS.
6. Completar nivel, temperatura y luz.

El `main.cpp` ya deja modelada esta secuencia para que puedas sustituir las funciones simuladas por drivers reales sin cambiar el flujo general.

## Observacion

El `main.cpp` usa funciones simuladas para las lecturas y una programacion local de riego 15/60. Eso permite validar primero la comunicacion HTTP con Flask/MySQL y luego reemplazar cada bloque por la lectura real o los GPIO definitivos.

## Flujo recomendado

1. Inicia sesion en EcoGrow.
2. Registra tu torre con su codigo unico.
3. Elige el cultivo activo de esa torre para la fase actual.
4. Coloca ese codigo en `TORRE_CODIGO`.
5. Compila y sube el firmware al ESP32.
