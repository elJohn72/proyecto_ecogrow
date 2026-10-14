# Informe técnico de presentación — EcoGrow

**Versión:** 2026-10-14 (actualiza el informe del 2026-07-14)
**Uso:** sustentación, pitch técnico, demo y onboarding
**Fuente de verdad:** repositorio https://github.com/elJohn72/proyecto_ecogrow
**Organización:** AJTecnology / AJENZA S.A.S.

---

## 1. Resumen ejecutivo

**EcoGrow** es un sistema de automatización agrícola por hidroponía. Une el panel web, la aplicación Android, el firmware de la torre y el diseño eléctrico en un solo producto.

| Pregunta | Respuesta |
|----------|-----------|
| Qué problema resuelve | Regar con trazabilidad y sin dejar la bomba en seco |
| Qué está implementado | Web, API, app Android, firmware ESP32 2.0, identidad de fábrica y diagrama de montaje |
| Qué ya se vio en la torre prototipo | Bluetooth, WiFi, vínculo a la cuenta y reporte al servidor |
| Qué falta para cerrar la prueba física | Lectura real de agua, encendido de la bomba y esquemático de fabricación |

La bomba de la torre 2.0 se conmuta con un MOSFET en el GPIO 25. El módulo relé se usó solo para oír un clic en el banco. No forma parte del montaje.

---

## 2. Problema y criterio de diseño

En una torre vertical el riego tiene que ser periódico y la bomba no puede trabajar sin agua. El pH y los nutrientes importan después de que el riego y el nivel ya estén estables.

EcoGrow mantiene el orden A0, A1, A2 y A3: primero la actuación, después el tiempo y el nivel, después la calidad de la solución. El firmware 2.0 ya contiene las rutinas de tiempo, nivel, pH, TDS y temperatura. Esas lecturas no se publican ni autorizan la bomba mientras el depósito y las sondas no estén calibrados.

Fuentes: `docs/producto/VISION-Y-LINEAS-ECOGROW.md` y `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md`.

---

## 3. Dos líneas de producto

| Línea | Qué produce | Estado |
|-------|-------------|--------|
| EcoGrow Plantas | Hortalizas de hoja en torre vertical | Prototipo en curso |
| EcoGrow Forraje | Forraje hidropónico para animales | Misma plataforma; el prototipo físico no está armado |

Comparten API, panel, app y controlador. Cambian los tiempos y el cultivo, no el programa de la placa.

---

## 4. Lo implementado

### 4.1 Plataforma web

| Capacidad | Dónde está |
|-----------|------------|
| Cuentas y sesión | `blueprints/auth.py` |
| Torres, fases y cosecha | `blueprints/torres.py` |
| Cultivos y PDF | `blueprints/cultivos.py` |
| Monitoreo, alertas y sync IoT | `blueprints/sensores.py` |
| API móvil: detalle, bomba, modo y receta | `blueprints/mobile.py`, `services/mobile_service.py` |
| Inventario de fábrica y vínculo con PIN | `claim_dispositivo_torre` en `Conexión/conexion.py` |
| Perfiles de pH y conductividad por fase | `domain/hidroponia_torre.py` |
| Asistente | `blueprints/ai.py` |
| Salud del servicio | `GET /health` |

El backend público está en Coolify, con HTTPS. El dispositivo no escribe en la base: envía `POST /api/iot/sync` con su token individual. El encendido remoto exige una lectura de agua de los últimos dos minutos y un nivel por encima del mínimo. Si el dato es viejo, el servidor rechaza la orden.

### 4.2 Aplicación Android

La app nativa está en `android/`, paquete `com.ecogrow.mobile`, con Kotlin y Jetpack Compose.

| Capacidad | Comportamiento |
|-----------|----------------|
| Cuenta | Registro e ingreso contra la API remota |
| Alta de torre | Bluetooth, PIN de la etiqueta, red de 2,4 GHz y contraseña |
| Servicio BLE | El mismo UUID que el firmware (`021a9004-0382-4aea-bff4-6b3f1b5adfb4`) |
| Detalle | Sensores, antigüedad de la lectura, modo y receta |
| Bomba | Encender solo con telemetría reciente y agua suficiente. Apagar solo si ya está encendida |

La app no muestra la dirección del servidor ni la contraseña de la red.

### 4.3 Firmware de la torre

El programa vigente es `platformio/esp32_ecogrow2/`. Sustituye al banco antiguo `platformio/esp32_rele_base/`, que mandaba un relé por el GPIO 26.

| Capacidad | Estado en código |
|-----------|------------------|
| Identidad | Código de torre y PIN de 8 caracteres en memoria. No se borran al cambiar de red |
| Bluetooth | Anuncio `PROV_EcoGrow_XXXX` mientras no hay red guardada |
| WiFi | La app envía la red. Si esa red no responde en cerca de un minuto, el Bluetooth vuelve a abrirse |
| Botón BOOT | De 3 a 8 segundos abre el Bluetooth y conserva el PIN. Doce segundos borra la torre |
| Reloj y HTTPS | Sincroniza la hora y valida el certificado del servidor |
| Sensores | Ultrasonido JSN-SR04T, TDS, pH y DS18B20. Sin calibrar, no envían número |
| Bomba | GPIO 25 en alto enciende. Sin nivel válido, la salida queda en bajo |
| Riego automático | Ciclo local de minutos encendido y apagado, con corte si falta agua |
| Sync | Cada 10 segundos, con acuse del comando que ejecutó |

### 4.4 Pines de montaje

| Señal | Pin |
|-------|-----|
| Bomba, gate del MOSFET IRLZ44N | GPIO 25, con 220 ohmios y 10 kiloohmios a masa |
| Ultrasonido, disparo | GPIO 5 |
| Ultrasonido, eco | GPIO 19, divisor 1 kiloohmio / 2 kiloohmios |
| TDS, señal | GPIO 34 |
| TDS, alimentación pulsada | GPIO 18 |
| pH | GPIO 35 |
| Temperatura DS18B20 | GPIO 32, con 4,7 kiloohmios a 3,3 V |
| Botón de bomba | GPIO 26 |
| Botón de modo | GPIO 27 |
| Recuperación | GPIO 0 |

El diagrama de armado está en `hardware/schematics/diagrama-electrico.md`. La orden para pasarlo a KiCad y gerbers está en `hardware/TALLER.md`. Aún no hay archivo de fabricación ni placa impresa.

### 4.5 Piezas 3D

El germinador está en `hardware/3d/germinador/estacion_germinacion_hidroponico.3mf`. La torre vertical impresa sigue pendiente.

---

## 5. Arquitectura

```text
App Android                         Panel web
BLE (solo alta y cambio de red)     HTTPS
HTTPS                               |
        \                          /
         Backend Flask en Coolify
         MariaDB
              ^
              | HTTPS, token de la torre
         ESP32
         MOSFET -> bomba 12 V
         Sensores del depósito
```

El teléfono no se queda en Bluetooth ni en la red local de la torre. Después del alta, el control sale por el servidor.

---

## 6. Lo probado en la torre prototipo

La placa en banco es la ESP32 de código `EG-TORRE-F870C4`, anuncio `PROV_EcoGrow_70C4`.

| Prueba | Resultado |
|--------|-----------|
| Anuncio Bluetooth y alta con el PIN de la etiqueta | Hecho |
| La torre entra a la red de 2,4 GHz | Hecho. Quedó con dirección en la red de casa |
| El servidor reconoce el token y el código | Hecho. El dispositivo figura vinculado |
| El sync HTTPS llega | Hecho. El servidor actualiza el estado reportado de la bomba |
| Lectura de sensores guardada | No. Depósito, pH y TDS están sin calibrar, y no hay cultivo activo |
| Encender la bomba desde la app | Bloqueado. No hay lectura de agua de los últimos dos minutos |
| Apagar desde la app | El botón permanece inactivo porque la bomba ya está apagada |
| Llevar la torre a otra red | Implementado en el firmware. Todavía no se hizo la prueba en otro lugar |
| Esquemático de fabricación | Pendiente de taller |

Al alimentar, el GPIO 25 queda en bajo. El relé o el MOSFET no deben cerrar solos.

---

## 7. Fases, con el estado de octubre de 2026

| Fase | Qué es | Estado |
|------|--------|--------|
| A0 | Actuar la bomba desde el sistema | El camino remoto existe. El clic físico de la bomba 2.0 no está aceptado |
| A1.1 | Riego por tiempo | Implementado en el firmware. Falta verlo en la torre con agua |
| A1.2 | Nivel y corte en seco | Implementado. No publica nivel hasta calibrar el depósito |
| A2 | pH, TDS y temperatura en operación | El código y el diagrama están. Las sondas no están calibradas ni guardando lecturas |
| A3 | Luz, dosificación y operación avanzada | No iniciado |
| Hardware de fabricación | KiCad, lista de materiales y gerbers | Orden abierta en `hardware/TALLER.md` |

---

## 8. Qué se puede decir y qué no

Se puede decir:

1. Hay plataforma web, API móvil y app Android.
2. La torre prototipo se dio de alta por Bluetooth, guardó el WiFi y reporta al servidor sin borrar su PIN.
3. La bomba está protegida: sin agua reciente no enciende, ni en la app ni en la placa.
4. El montaje eléctrico de la versión 2.0 está escrito y alineado con el firmware.

No se afirma:

1. Que la bomba ya haya regado en la torre.
2. Que el pH, el TDS o el nivel estén medidos en campo.
3. Que exista placa fabricada.
4. Que la línea de forraje tenga prototipo físico.

---

## 9. Próximo cierre

| Orden | Hito |
|-------|------|
| 1 | Armar la baquelita según el diagrama: MOSFET, diodo y sensores |
| 2 | Calibrar el depósito y guardar la primera lectura de agua |
| 3 | Encender y apagar la bomba desde la app, con la torre fuera del computador |
| 4 | El taller entrega el KiCad y, cuando corresponda, los gerbers de la revisión A |

---

## 10. Referencias

| Recurso | Ruta |
|---------|------|
| Repositorio | https://github.com/elJohn72/proyecto_ecogrow |
| Firmware de la torre | `platformio/esp32_ecogrow2/` |
| App Android | `android/` |
| Diagrama | `hardware/schematics/diagrama-electrico.md` |
| Orden de taller | `hardware/TALLER.md` |
| Visión de producto | `docs/producto/VISION-Y-LINEAS-ECOGROW.md` |
| Roadmap | `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md` |
| Germinador | `hardware/3d/germinador/` |

La guía `docs/iot/FASE1-ESP32-BOMBA-RELE.md` describe el banco viejo con relé en el GPIO 26. No se usa para montar esta torre.

---

*Informe actualizado el 14 de octubre de 2026 a partir del código y de la prueba de la torre prototipo. No sustituye el expediente de fabricación que debe cerrar el taller.*
