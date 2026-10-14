# Diagrama eléctrico — EcoGrow 2.0

Revisión **2.0-proto**. Baquelita. El taller la pasa a KiCad según [../TALLER.md](../TALLER.md). La prueba por etapas está en [../BANCO.md](../BANCO.md).

Los pines coinciden con `platformio/esp32_ecogrow2/src/main.cpp`. No se mueven.

La bomba de 12 V se conmuta con MOSFET en el GPIO 25. No va a un módulo relé ni al GPIO 26. Ningún sensor de potencia se alimenta desde un GPIO.

## Lo que todavía no está medido

Estas cifras no se inventan. Hay que leerlas en la pieza o en el multímetro y anotarlas en la guía de banco antes de energizar esa etapa:

- Marcado exacto del módulo JSN-SR04T y su zona muerta.
- Marcado del módulo de pH y tensión de su salida analógica.
- Marcado del módulo TDS y tensión de su salida analógica.
- Tensión, corriente nominal y corriente de arranque de la bomba.
- Marcado del MOSFET (tiene que leerse IRLZ44N, no IRFZ44N).
- Tensión real del buck en vacío.
- Si en la mesa hay un NPN 2N3904 además del PNP 2N3906.

El chip visto en un grabado anterior de esta placa fue un ESP32-D0WD-V3. Eso no identifica el módulo de desarrollo ni valida sensores o bomba. La ESP32 ya se probó sin sensores: Bluetooth, WiFi y reporte HTTPS. Esa prueba no calibra nada.

## Alimentación

Una sola fuente de 5 V hacia la ESP32. No se conectan a la vez el USB y la salida del buck: en estas placas el VIN puede devolver tensión hacia el computador.

```text
Fuente 12 V
  (+) ----+---- bomba (+)
          |
          +---- entrada del buck
          |
          +---- cátodo del diodo volante (banda), en el +12 V

  (-) ---- GND común
           Source del MOSFET, GND del buck, GND del ESP32 y GND de sensores
           unidos en un solo punto

Buck, salida medida en vacío antes de tocar el ESP32
  OUT+ --> VIN del ESP32
  OUT- --> GND
```

El valor de 5,00 V es el ajuste pedido, no una medición hecha en esta mesa. Si el buck no se queda en 5,00 V ± 0,05 V, no se conecta la placa.

## Bomba

```text
GPIO 25 ---- 220 Ω ---- Gate del MOSFET
                         |
                        10 kΩ
                         |
                        GND

Bomba (-) ---- Drain
Source -------- GND
Diodo entre +12 V (cátodo, banda) y Drain (ánodo)
```

Al arrancar, el firmware deja el GPIO 25 en bajo. Sin nivel calibrado y reciente la salida no pasa a alto.

El IRLZ44N publica Rds(on) a 4 V y a 5 V. La tensión de umbral no demuestra que conduzca bien con 3,3 V en el gate. Antes de dejar la bomba conectada se mide la caída drain-source con la corriente real. Si esa potencia no cabe en el encapsulado, se corta la prueba.

El 1N5819 es un Schottky de 1 A de media. Si la corriente de la bomba, leída en su placa o medida en serie, no deja margen bajo ese amperio, no se usa este diodo. No se elige otro sin esa corriente.

La salida en alto significa que el GPIO ordenó conducir. No hay sensor de corriente ni de caudal: no demuestra que el agua se mueva.

## Ultrasonido

El ECHO de un módulo a 5 V no entra directo al GPIO 19. El divisor anterior de 1 kΩ / 2 kΩ deja unos 3,33 V con un eco de 5,00 V y puede pasar de 3,3 V con tolerancia del 5 % y un eco de 5,25 V.

Divisor de esta revisión:

```text
ECHO ---- 2,2 kΩ ---- GPIO 19
                       |
                     3,3 kΩ
                       |
                      GND
```

Con eco de 5,00 V el GPIO ve unos 3,0 V. Con 5,25 V y resistencias al 5 % en el peor sentido sigue por debajo de 3,3 V. TRIG sale del GPIO 5 a 3,3 V. Si el módulo que está en la mesa exige disparo a 5 V, no se conecta hasta poner un adaptador; no se supone por el aspecto.

VCC del módulo a 5 V, no a un GPIO. GND al punto común.

## TDS

El firmware pone el GPIO 18 en alto durante la lectura y lo devuelve a bajo. Un PNP 2N3906 con el emisor a 5 V no se apaga con un alto de 3,3 V: la base quedaría 1,7 V por debajo del emisor y el transistor seguiría conduciendo. La base no se conecta directa al GPIO.

Circuito que respeta ese alto:

```text
GPIO 18 ---- 1 kΩ ---- base del NPN 2N3904
emisor del NPN -------------- GND
colector del NPN ----+---- base del PNP 2N3906
                      |
                    10 kΩ
                      |
                     +5 V y emisor del PNP

colector del PNP ---- VCC del módulo TDS
GND del módulo ------ GND
salida analógica ---- GPIO 34, solo si antes mide ≤ 3,30 V
```

GPIO 18 en bajo, o la placa recién arrancada: el NPN está cortado, la base del PNP queda a 5 V y el TDS no tiene alimentación. GPIO 18 en alto: el TDS se alimenta el tiempo de la lectura.

Sin el NPN, no se arma esta etapa.

## pH

VCC del módulo a 5 V. GND común. La salida analógica va al GPIO 35 solo después de medirla con el módulo alimentado y la sonda fuera del GPIO. Si esa salida pasa de 3,30 V, no se conecta: se ajusta el módulo o se agrega un divisor medido. El firmware no recorta una saturación y la presenta como pH.

## Temperatura

DS18B20: datos al GPIO 32, 4,7 kΩ desde el datos hacia 3,3 V, VCC a 3,3 V y GND común. No se alimenta la sonda desde un GPIO.

## Pines

| Pin | Función |
|---|---|
| GPIO 25 | Gate del MOSFET de la bomba |
| GPIO 5 | TRIG del ultrasonido |
| GPIO 19 | ECHO, después del divisor |
| GPIO 34 | Analógico TDS, máximo 3,3 V |
| GPIO 18 | Enciende el TDS mediante NPN y PNP |
| GPIO 35 | Analógico pH, máximo 3,3 V |
| GPIO 32 | Datos del DS18B20 |
| GPIO 26 | Botón de bomba |
| GPIO 27 | Botón de modo |
| GPIO 0 | BOOT. 3 a 8 s cambia el WiFi y conserva el PIN. 12 s borra la torre |
| GPIO 2 | LED de la placa |

## Tabla de conexión y medición previa

La columna de medición queda pendiente hasta el multímetro. No se llena con un valor supuesto.

| Punto | Conexión | Tensión esperada antes de seguir | Medición |
|---|---|---|---|
| Buck, vacío, ESP32 desconectado | Salida del buck | 5,00 V ± 0,05 V | PENDIENTE |
| VIN de la ESP32 | Buck, sin USB | La misma salida del buck | PENDIENTE |
| GPIO 25 al arrancar | Gate, pull-down 10 kΩ | 0 V y la bomba quieta | PENDIENTE |
| GPIO 25 ordenado en alto, sin bomba | Gate | Cerca de 3,3 V | PENDIENTE |
| Drain a source con la bomba | MOSFET ya identificado | Caída baja; si calienta, se corta | PENDIENTE |
| ECHO en el GPIO 19 | 2,2 kΩ / 3,3 kΩ | Pulso ≤ 3,30 V | PENDIENTE |
| GPIO 18 en reposo | Base del NPN | 0 V y VCC del TDS en 0 V | PENDIENTE |
| Salida TDS | GPIO 34 | ≤ 3,30 V con el módulo alimentado | PENDIENTE |
| Salida pH | GPIO 35 | ≤ 3,30 V antes de soldarla al pin | PENDIENTE |
| DS18B20 VCC | 3,3 V | 3,3 V, no 5 V | PENDIENTE |
| +12 V | Fuente de la bomba | La tensión impresa en la fuente, no una suposición | PENDIENTE |

## Baquelita

Placa perforada de 7 × 9 cm. La ESP32 va en zócalo. El 12 V de la bomba se refuerza con hilo de 0,6 a 0,8 mm. El retorno de potencia y el GND lógico se unen en un punto. pH y TDS no corren junto al cable de la bomba. Un condensador de 100 nF en la alimentación de cada módulo analógico, junto al módulo, si el módulo no lo trae ya. Eso no sustituye la medición.
