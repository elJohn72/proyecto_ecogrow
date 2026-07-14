# Informe técnico de presentación — EcoGrow

**Versión:** 2026-07-14  
**Uso:** sustentación, pitch técnico, competencia / demo, onboarding  
**Fuente de verdad:** repositorio público  
https://github.com/elJohn72/proyecto_ecogrow  
**Landing complementaria:** https://github.com/elJohn72/Ecogrow.io  
**Organización:** AJTecnology / AJENZA S.A.S.

---

## 1. Resumen ejecutivo

**EcoGrow** es un sistema de **automatización de procesos agrícolas** basado en hidroponía e IoT. Integra en un solo flujo:

1. **Software de gestión** (panel web Flask + MySQL).
2. **Control embebido** (ESP32 + relé + bomba).
3. **Dominio agronómico** (perfiles por fase de cultivo).
4. **Hardware físico / 3D** (torre, germinador, forraje).

No se trata solo de un prototipo aislado: el repositorio documenta una **plataforma evolutiva** con dos líneas de producto y un plan de automatización por fases, de modo que cada entrega de hardware o firmware tenga criterio de salida claro.

| Pregunta | Respuesta breve |
|----------|-----------------|
| ¿Qué problema resuelve? | Controlar riego, trazabilidad y (próximo) calidad de solución sin depender de operación 100 % manual |
| ¿Qué entregamos hoy? | Panel web completo + IoT de bomba (A0) + germinador 3D + roadmap A1–A3 |
| ¿Hacia dónde va? | A1: bomba por tiempo + nivel; A2: nutrientes; A3: ambiente y dosificación |

---

## 2. Problema y justificación técnica

### 2.1 Contexto

En hidroponía (torre vertical o forraje):

- El **riego** debe ser periódico y predecible.
- La bomba no puede operar en seco (daño de equipo y pérdida de cultivo).
- pH y EC importan, pero **solo tienen valor operativo** si el sistema ya riega y protege el depósito de forma estable.
- Un laboratorio o finca piloto necesita **trazabilidad**: torre, ciclo, fase, lecturas, cosecha.

### 2.2 Argumento de diseño

Muchos proyectos IoT agrícolas intentan instalar todos los sensores al mismo tiempo. Eso genera:

- fallos difíciles de diagnosticar (¿falla el WiFi, el pH o el relé?);
- dependencia de calibración antes de tener riego confiable;
- software complejo sin base física estable.

**EcoGrow invierte el orden:** primero **actuación confiable** (bomba), luego **protección** (nivel), después **calidad de solución** (pH/EC). Ese orden está formalizado en el repositorio como fases A0 → A1 → A2 → A3.

Fuentes en GitHub:

- `docs/producto/VISION-Y-LINEAS-ECOGROW.md`
- `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md`

---

## 3. Visión de producto — dos líneas

EcoGrow no es “solo lechuga en torre”. Es la marca de **automatización agrícola** con dos vertientes que comparten software y firmware:

| Línea | Nombre | Qué produce | Usuarios / escenario |
|-------|--------|-------------|----------------------|
| **A** | EcoGrow Plantas | Hortalizas de hoja en **torre vertical** (lechuga, berro, cilantro, hierbas) | Laboratorio, club, demo urbana, competencia |
| **B** | EcoGrow Ganadero / Forraje | **Forraje hidropónico** para vacas, cerdos, aves y otros animales | Finca, ganadería, demo Agrotech |

### Argumento comercial-técnico

- **Misma plataforma IoT** (API, panel, ESP32) reduce costo de desarrollo.
- **Parámetros distintos** (tiempos ON/OFF, densidades, ciclos) se configuran por línea, no se hardcodean en firmware.
- Permite demostrar **impacto alimentario** (vegetales) y **impacto pecuario** (forraje) con un solo stack.

Documento canónico: `docs/producto/VISION-Y-LINEAS-ECOGROW.md`.

---

## 4. Lo desarrollado (evidencia en el repositorio)

### 4.1 Software de gestión (hecho)

| Capacidad | Evidencia en repo | Valor para la presentación |
|-----------|-------------------|----------------------------|
| Autenticación multi-usuario | `blueprints/auth.py`, Flask-Login | Seguridad básica y sesiones |
| Torres + ciclo de cultivo | `blueprints/torres.py` | Trazabilidad por unidad física |
| CRUD cultivos + PDF | `blueprints/cultivos.py`, `services/`, fpdf2 | Entregable académico y operativo |
| Monitoreo y alertas | `blueprints/sensores.py`, setpoints | Panel de control central |
| Perfiles pH/EC por fase | `domain/hidroponia_torre.py` | Dominio agronómico en código |
| Agricultor IA | `blueprints/ai.py`, Gemini | Asistencia al operador |
| Despliegue cloud | `render.yaml`, Gunicorn | Listo para demo en línea |
| Salud del servicio | `GET /health` | Operación y monitoreo |

Documentación maestra: `docs/DOCUMENTACION-PROYECTO-ECOGROW.md`.

### 4.2 Arquitectura (argumento de ingeniería)

```text
Navegador (Jinja2 + CSS)
        │ HTTPS
        ▼
Flask (blueprints: auth · torres · cultivos · sensores · ai)
        │
        ▼
Conexión/conexion.py  ──►  MySQL / MariaDB
        ▲
        │ JSON + X-API-Token
        │
   ESP32 (PlatformIO)
   relé → bomba  (+ futuros sensores)
```

**Por qué esta arquitectura**

- **Capas claras:** UI → controladores → dominio → datos → firmware.
- **Blueprints** permiten crecer por módulo sin monolito ilegible.
- El ESP32 **no escribe directo en MySQL**: usa API con token → aislamiento y seguridad.
- El dominio agronómico (`domain/`) evita mezclar “magia de pH” dentro de las rutas HTTP.

Detalle: sección 4 de `docs/DOCUMENTACION-PROYECTO-ECOGROW.md` y `docs/ESTRUCTURA-PROYECTO.md`.

### 4.3 Stack tecnológico

| Capa | Tecnología | Rol |
|------|------------|-----|
| Backend | Python 3, Flask 3.x, Flask-Login | Aplicación web |
| Datos | MySQL / MariaDB | Persistencia relacional |
| Frontend | Jinja2, CSS propio, Bootstrap 5 | Panel operador |
| Reportes | fpdf2 | PDF de cultivos |
| IA | Google Generative AI (Gemini) | Asistente operativo |
| IoT | ESP32, PlatformIO, HTTP/JSON | Actuación y telemetría |
| Cloud | Render + Gunicorn | Hosting |

### 4.4 IoT — automatización por fases

| Fase | Qué hace | Estado en repo (jul-2026) | Criterio de salida |
|------|----------|---------------------------|--------------------|
| **A0** | Bomba manual desde panel vía `POST /api/iot/sync` | **Hecho** — `platformio/esp32_rele_base/` | Relé obedece comando del servidor |
| **A1.1** | Bomba por **tiempo** (ON/OFF programado) | **Prioridad / en curso** | Ciclo automático sin intervención cada ON/OFF |
| **A1.2** | **Nivel de agua** + no bombear en seco | **Pendiente prioritario** | Alerta + corte de bomba con depósito bajo |
| **A2** | Sensores nutrientes (pH, EC, T°) | **Después de A1** — `esp32_hidroponico/` | Lecturas reales + alertas por fase |
| **A3** | Luz/DLI, recetas A/B, IPM, 3D torre/forraje | Posterior | Operación avanzada |

Guías:

- `docs/iot/FASE1-ESP32-BOMBA-RELE.md` (cableado A0)
- `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md` (orden oficial)
- `docs/iot/GUIA-ESP32-RELE.md` (API)

**Argumento para el jurado / audiencia:**  
“No prometemos una granja automática completa. Demostramos una **cadena de control verificable**: hoy la bomba responde al sistema; el siguiente hito es tiempo + nivel; los nutrientes vienen cuando la base no falla.”

### 4.5 Hardware 3D — germinador

| Entregable | Ruta en GitHub |
|------------|----------------|
| Modelo 3MF estación de germinación | `hardware/3d/germinador/estacion_germinacion_hidroponico.3mf` |
| Documentación de uso | `hardware/3d/germinador/README.md` |

**Argumento:** cierra el ciclo cultivo desde **germinación → torre/forraje → monitoreo digital**, y evidencia capacidad de diseño/fabricación (impresión 3D) además de software.

### 4.6 Documentación y especificaciones

| Material | Ubicación |
|----------|-----------|
| Documentación completa | `docs/DOCUMENTACION-PROYECTO-ECOGROW.md` |
| Presentación diapositivas (20 slides) | `documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md` |
| Manual dominio torre | `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md` |
| Specs | `specs/001-auditoria-web/`, `specs/002-dominio-hidroponia-torre/` |
| Este informe | `documentacion_equipo/entregables/INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.md` |

---

## 5. Flujo operativo que se puede demostrar

### 5.1 Ciclo de cultivo (software)

```text
Registrar torre → Seleccionar cultivo → Iniciar/cambiar fase
→ Telemetría / monitoreo → Cosecha o cierre de ciclo
```

### 5.2 Cadena IoT A0 (hardware + API)

```text
Panel web → comando bomba → MySQL (estado actuador)
     → ESP32 sync (cada N s) → relé → bomba ON/OFF
```

Token de dispositivo: header `X-API-Token` (`ECOGROW_SENSOR_API_TOKEN`).  
Failsafe: si se pierde WiFi/API, el firmware apaga la bomba (protección documentada).

### 5.3 Próxima demo A1 (mensaje de roadmap)

```text
Programación riego (min ON / min OFF) → modo automático
+ sensor de nivel → bloqueo bomba en seco + alerta en panel
```

Misma lógica aplicable a **torre vegetal** y **bandejas de forraje**, con tiempos distintos.

---

## 6. Resultados y estado actual (qué decir en voz alta)

### Ya construido y versionado

1. Plataforma web académica/operativa con auth, torres, cultivos, PDF, alertas e IA.
2. Integración IoT real de **actuación** (ESP32 + relé + bomba).
3. Dominio agronómico en código (perfiles por fase).
4. Visión de negocio de **dos líneas** documentada en GitHub.
5. Roadmap de automatización **ordenado y argumentado**.
6. Modelo 3D del germinador publicado en el repo.

### En curso (honestidad técnica)

- Cerrar **A1.1** (riego por tiempo) de punta a punta en `main` (hay avances locales de firmware/API a consolidar).
- Implementar **A1.2** (nivel de agua) en hardware y lógica.

### No se afirma aún

- Dosificación automática de nutrientes en campo.
- App móvil nativa comercial.
- Que pH/EC en producción ya midan con sondas calibradas (capa A2 pendiente).

---

## 7. Roadmap de presentación (próximos hitos)

| Prioridad | Hito | Mensaje al público |
|-----------|------|--------------------|
| 1 | A1.1 Bomba por tiempo en producción | “El sistema riega solo por programa” |
| 2 | A1.2 Nivel + anti-seco | “Protegemos la bomba y el cultivo” |
| 3 | Prototipo forraje con mismos controladores | “Misma plataforma, segunda línea de negocio” |
| 4 | A2 Sensores pH/EC reales | “Pasamos de riego a calidad de solución” |
| 5 | A3 Luz / nutrientes A-B / IPM | “Operación avanzada” |

---

## 8. Conclusión

EcoGrow demuestra que se puede construir **automatización agrícola seria** sin saltarse la ingeniería:

- **Producto claro:** dos líneas (vegetales en torre + forraje animal).
- **Plataforma real:** web + BD + ESP32 + documentación abierta en GitHub.
- **Método:** fases A0–A3, con criterios de salida y sin vender capacidades no estabilizadas.

El repositorio no solo guarda código: guarda la **argumentación del desarrollo** — qué se hizo, por qué en ese orden y qué viene después.

---

## 9. Referencias rápidas (para anexos / QR)

| Recurso | URL / ruta |
|---------|------------|
| Repo principal | https://github.com/elJohn72/proyecto_ecogrow |
| Visión 2 líneas | `docs/producto/VISION-Y-LINEAS-ECOGROW.md` |
| Roadmap automatización | `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md` |
| Doc completa | `docs/DOCUMENTACION-PROYECTO-ECOGROW.md` |
| Diapositivas 20 slides | `documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md` |
| Germinador 3D | `hardware/3d/germinador/` |
| Guía bomba A0 | `docs/iot/FASE1-ESP32-BOMBA-RELE.md` |

---

## 10. Guión sugerido (8–12 minutos)

| Min | Bloque |
|-----|--------|
| 0–1 | Problema: riego manual, sin trazabilidad, riesgo de bomba en seco |
| 1–3 | Visión EcoGrow: automatización agrícola, 2 líneas |
| 3–6 | Demo / diagrama: panel + MySQL + ESP32 + bomba (A0) |
| 6–8 | Por qué las fases (A1 tiempo+nivel antes que pH/EC) |
| 8–10 | Germinador 3D + hardware físico |
| 10–12 | Roadmap A1–A3 y cierre |

---

*Informe sintetizado desde la documentación y código publicados en GitHub (`proyecto_ecogrow`). Actualizar este archivo cuando A1 quede cerrado en `main`.*
