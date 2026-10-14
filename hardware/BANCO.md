# Banco de la torre — sensores y bomba

Orden para conectar y probar. No se enchufa todo junto. Cada etapa se hace con la fuente desconectada, se mide, y solo entonces se energiza.

La ESP32 de esta torre ya se probó **sin sensores**: se dio de alta por Bluetooth, guardó el WiFi y el servidor recibió el reporte. Eso no valida nivel, pH, TDS, temperatura ni bomba.

Código de la torre en banco: `EG-TORRE-F870C4`. Anuncio Bluetooth: `PROV_EcoGrow_70C4`.

La calibración se guarda en la memoria de la torre con comandos por USB. No borra el PIN, el WiFi ni el token. No se usa el borrado de 12 segundos para calibrar. No se pone en verdadero un flag de ejemplo para ver números.

Umbral de software, igual en firmware, app y servidor cuando el servidor tenga este cambio: la salida se corta en el nivel mínimo configurado (por defecto 20 %) y no vuelve a armarse hasta 5 puntos por encima (25 %). No es la inmersión medida de la bomba. Esa cifra se anota aquí cuando se lea la bomba, y entonces se cambia el mínimo en el panel.

La salida en alto no es caudal. No hay sensor de corriente ni de flujo.

## Datos que John tiene que anotar antes de la etapa correspondiente

| Dato | Dónde leerlo | Valor |
|---|---|---|
| Módulo de la ESP32, además del chip | Serigrafía de la placa | |
| JSN-SR04T: texto de la placa y zona muerta del fabricante | Hoja o impreso del módulo | |
| Módulo de pH | Texto del impreso | |
| Módulo TDS | Texto del impreso | |
| Bomba: tensión, corriente nominal, arranque | Etiqueta del motor o medición en serie | |
| MOSFET | Tiene que decir IRLZ44N | |
| Buck en vacío | Multímetro | |
| Hay 2N3904 y 2N3906 | Marcado de los transistores | |

Si falta el dato de esa etapa, esa etapa queda en PENDIENTE. No se sustituye por un módulo parecido.

## Comandos de banco

Monitor a 115200. La identidad no se imprime en el diagnóstico.

| Comando | Efecto |
|---|---|
| `ECOGROW:DIAG` | Estado, crudo, convertido y si está calibrado. Pulsa el TDS una vez |
| `ECOGROW:CAL_TANK:altura,minimo,litros,lineal` | Ejemplo de forma: `ECOGROW:CAL_TANK:40,25,18,0`. El cuarto número es 1 solo si el volumen es lineal con la altura |
| `ECOGROW:CAL_TANK_CLEAR` | Borra solo la calibración del depósito |
| `ECOGROW:CAL_PH:v1,ph1,v2,ph2` | Dos soluciones de referencia ya medidas en voltios |
| `ECOGROW:CAL_PH_CLEAR` | Borra solo el pH |
| `ECOGROW:CAL_TDS:factor` | Factor entre 0,2 y 5, después de la solución de referencia del módulo real |
| `ECOGROW:CAL_TDS_CLEAR` | Borra solo el TDS |

Un ADC pegado a 0 o a 3,3 V sale como saturado y no se publica. Un pin analógico suelto puede dar un número a mitad de escala: eso no se acepta como medición. El programa no promete detectar esa desconexión.

## Etapas

### 1. Fuente y buck

Componentes: fuente de 12 V, buck, multímetro. ESP32, sensores y bomba desconectados.

Conexión con la fuente apagada. Ajusta el buck sin carga. Mide la salida.

Esperado: 5,00 V ± 0,05 V, estable. USB desconectado cuando el buck alimente el VIN.

Seguir solo si esa medición se anota. Si sube de 5,2 V o oscila, no conectar la ESP32.

Estado: PENDIENTE.

### 2. DS18B20

Componentes: sonda, resistencia 4,7 kΩ a 3,3 V, GPIO 32. Sin bomba.

Alimentación apagada para soldar. Después, solo la lógica. El informe serial, cada 15 s o con `ECOGROW:DIAG`, debe pasar de `desconectado` a `ok` con grados reales. Fuera de 0 °C a 60 °C queda fuera de rango y no compensa el TDS.

Seguir si el estado es `ok` y el número cambia al tocar la sonda. Si sigue en desconectado, revisar alimentación, datos y la resistencia. No inventar la temperatura.

Estado: PENDIENTE.

### 3. Nivel

Componentes: JSN-SR04T confirmado, TRIG al GPIO 5, ECHO con 2,2 kΩ y 3,3 kΩ hacia el GPIO 19, VCC a 5 V.

Medir el pulso en el GPIO 19 antes de darlo por bueno: no pasa de 3,30 V. Medir la distancia a un blanco quieto y compararla con una regla. Anotar la zona muerta real. Vacío y lleno del depósito se miden, no se copian de los 40 cm y 10 cm de ejemplo.

`ECOGROW:DIAG` muestra centímetros en crudo aunque no esté calibrado. El porcentaje sale `nan` hasta `ECOGROW:CAL_TANK`. Si el tanque no es de sección constante, el cuarto parámetro va en 0 y no se publican litros.

Seguir cuando la distancia sea estable y el porcentaje coincida con el agua medida. Timeout o fuera de rango: no calibrar encima.

Estado: PENDIENTE.

### 4. pH

Componentes: el módulo identificado, no uno parecido. VCC a 5 V. La salida se mide con el multímetro antes de tocar el GPIO 35.

Si pasa de 3,30 V, no se conecta. Con dos soluciones de referencia, anotar voltios y pH de cada una y enviar `ECOGROW:CAL_PH`. El programa no recorta el resultado a 0–14.

Seguir si las dos soluciones se leen cerca de su valor y una sonda al aire no se publica como pH válido cuando satura. Si el número no se mueve entre las dos soluciones, no se usa.

Estado: PENDIENTE.

### 5. TDS

Componentes: NPN 2N3904, PNP 2N3906, 1 kΩ, 10 kΩ, módulo TDS identificado. Sin el NPN no se alimenta.

Con la fuente de lógica encendida y sin orden de lectura, el VCC del TDS está a 0 V. `ECOGROW:DIAG` lo pulsa un momento. Medir la salida analógica: ≤ 3,30 V. Calibrar con la solución que indique ese módulo y `ECOGROW:CAL_TDS`. La compensación usa la temperatura solo si el DS18B20 está en `ok`.

Anotar el número con la bomba apagada. El ruido con la bomba encendida se mira en la etapa 8.

Seguir si en reposo el módulo está apagado y, al diagnosticar, el valor se acerca a la referencia. Si el VCC queda siempre en 5 V, el transistor está mal y se desconecta.

Estado: PENDIENTE.

### 6. MOSFET sin bomba

Componentes: IRLZ44N confirmado, 220 Ω, 10 kΩ, diodo todavía sin la bomba. GPIO 25 al gate.

Al alimentar, gate a 0 V y sin clic. No se cierra el MOSFET con un cable al 3,3 V permanente. La prueba de salida alta se hace cuando ya exista un nivel calibrado que permita armar, o se observa solo el gate en una orden rechazada: si el nivel no es válido, el gate tiene que seguir en 0 V.

Esperado: arranque en bajo. Un alto medido en el gate no es un motor girando.

Si al alimentar el gate sube solo, desconectar y revisar el pull-down.

Estado: PENDIENTE.

### 7. Bomba con agua

Solo después del nivel calibrado y del MOSFET en bajo al arrancar. La bomba va entre +12 V y el drain. El diodo se monta si la corriente medida cabe en 1 A; si no, se para.

Depósito con agua por encima del armado (25 % con el mínimo por defecto). Pulsos cortos, con el límite manual del firmware (como máximo 15 minutos, y antes si la receta es más corta). John presente. La mano no está en el acople.

Esperado: el agua se mueve y, al bajar del corte o al quitar el eco, la salida cae sin esperar un ciclo largo. Apagar desde la app o el botón tiene prioridad sobre encender.

Si no gira, no se declara éxito por ver el GPIO en alto. Si el MOSFET se calienta, se corta la alimentación.

Estado: PENDIENTE.

### 8. Sensores con la bomba en marcha

Repetir nivel, temperatura, pH y TDS con la bomba un momento en marcha y otro en reposo. Anotar cuánto se mueve cada lectura. Un salto que pegue el ADC a un extremo invalida esa muestra: el estado tiene que dejar de ser `ok`.

Estado: PENDIENTE.

### 9. Datos móviles

Teléfono en datos, no en el WiFi de la torre. La app habla con el servidor. Encender solo con nivel reciente y por encima del armado. Apagar tiene que poder hacerse con la telemetría vieja.

El acuse remoto y el caudal no quedan demostrados hasta anotar aquí la hora en que la bomba cambió de verdad.

Estado: PENDIENTE.

### 10. Reinicio y recuperación

Quitar la alimentación y volver a darla: la bomba sigue apagada. Un corte de WiFi de menos de un minuto no debe abrir el Bluetooth ni borrar la red. El fin del aprovisionamiento, con IP ya obtenida, no borra la red al minuto. BOOT de 3 a 8 segundos cambia la red y conserva el PIN. Doce segundos borra la torre: no se usa en esta prueba.

Estado: PENDIENTE. La conectividad sin sensores, hecha antes, queda como PASÓ solo en ese alcance.

## Resultado de esta preparación

| Prueba | Estado |
|---|---|
| ESP32 sin sensores: Bluetooth, WiFi y reporte al servidor | PASÓ, en la prueba anterior. No incluye sensores ni bomba |
| Tensiones de fuente y buck | PENDIENTE |
| DS18B20 | PENDIENTE |
| Nivel calibrado | PENDIENTE |
| pH | PENDIENTE |
| TDS | PENDIENTE |
| Gate sin bomba | PENDIENTE |
| Bomba con agua | PENDIENTE |
| Sensores durante el bombeo | PENDIENTE |
| Control con datos móviles | PENDIENTE |
| Reinicio sin encendido sorpresa | PENDIENTE |

Grabar este firmware no borra la partición NVS si se usa la carga normal de PlatformIO, sin borrar toda la flash. No se ejecuta un borrado de flash para esta prueba.
