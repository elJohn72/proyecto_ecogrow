# Orden de taller — pulir el hardware

Revisión de partida: **2.0-proto**, baquelita, octubre 2026.

El diagrama de [schematics/diagrama-electrico.md](schematics/diagrama-electrico.md) es la base para armar el prototipo. No es el archivo de fabricación. El taller lo pule hasta dejar un esquemático que se pueda construir y repetir. La prueba por etapas está en [BANCO.md](BANCO.md).

## Qué hay que entregar

1. Esquemático en KiCad, en `hardware/schematics/`, con el nombre `ecogrow-torre-2.0`.
2. Lista de materiales de esa misma revisión, en `hardware/schematics/`.
3. Cuando la placa reemplace la baquelita, los gerbers de esa revisión en `hardware/gerbers/`.
4. Número de revisión en el archivo y en el sedoso o la placa. La primera placa fabricada es la revisión A.

Cada entrega tiene que coincidir con los pines de `platformio/esp32_ecogrow2/src/main.cpp`. Si un pin cambia, el firmware cambia en el mismo paso. No se deja el dibujo adelante del programa que está en la torre.

## Qué no se cambia

- La bomba de 12 V entra por el MOSFET **IRLZ44N** en el GPIO **25**, con 220 Ω al gate, 10 kΩ a GND y el diodo **1N5819**.
- El módulo relé no forma parte de la torre. Sirvió para probar el clic en el banco.
- El GPIO **26** no es la salida de la bomba. En este firmware es un botón.
- Ultrasonido: TRIG en GPIO **5**, ECHO en GPIO **19** con divisor 2,2 kΩ en serie y 3,3 kΩ a GND.
- TDS en GPIO **34**. El GPIO **18** en alto enciende la alimentación solo con NPN 2N3904 más PNP 2N3906. La base del PNP no va directa al GPIO.
- pH en GPIO **35**. DS18B20 en GPIO **32** con 4,7 kΩ a 3,3 V.
- El 1N5819 y la conducción del IRLZ44N a 3,3 V se confirman con la corriente medida de la bomba. Si la pieza no es IRLZ44N, o la corriente no cabe en el diodo, se para el montaje.
- El buck se ajusta a 5,00 V en vacío antes de conectar el ESP32.
- No se borra el PIN de la etiqueta ni la memoria de la torre para pulir el dibujo.

## Cómo se da por pulido

El taller cierra una revisión cuando el esquemático, la lista de materiales y, si ya hay placa, los gerbers dicen el mismo número, y una torre armada con eso enciende sin clic al alimentar y mantiene la bomba apagada hasta tener un nivel de agua válido.
