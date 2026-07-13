# EcoGrow — roadmap de automatización por fases

**Estado:** vigente (John, 2026-07-13)  
**Aplica a:** línea torre vegetal **y** línea forraje hidropónico  
**Visión de producto:** [`../producto/VISION-Y-LINEAS-ECOGROW.md`](../producto/VISION-Y-LINEAS-ECOGROW.md)

---

## Regla de oro

Automatizar **en orden**. No avanzar a nutrientes (pH/EC) hasta que la fase anterior esté **estable en banco** (y preferible en prototipo físico).

```text
A0 Manual → A1 Tiempo + nivel → A2 Nutrientes (pH/EC/T°) → A3 Ambiente / luz / avanzado
```

---

## Fase A0 — Control manual de bomba (base)

**Objetivo:** el panel enciende/apaga la bomba; el ESP32 aplica el comando.

| Elemento | Estado típico |
|----------|---------------|
| ESP32 + relé + bomba | Hecho (firmware `platformio/esp32_rele_base/`) |
| API `POST /api/iot/sync` | Hecho |
| Failsafe WiFi/API | Hecho |
| Guía | [`FASE1-ESP32-BOMBA-RELE.md`](FASE1-ESP32-BOMBA-RELE.md) |

**Criterio de salida:** bomba responde desde Monitoreo / panel en torre o banco.

---

## Fase A1 — Bomba por tiempo + nivel de agua ← **AHORA**

**Objetivo:** riego automático por **ciclo ON/OFF (tiempo)** y protección / lógica por **nivel de agua** en el depósito.

### A1.1 Bomba por tiempo

| Qué | Detalle |
|-----|---------|
| Software | `programaciones_riego` (minutos ON / OFF, habilitado) |
| Panel | `/irrigation` y configuración de torre |
| Firmware | Modo automático: ciclo local entre syncs + sync con EcoGrow |
| Estrategia | Oxigenación / recirculación según perfil (torre o forraje) |

**Criterio de salida A1.1:** en modo automático, la bomba cicla sola según minutos ON/OFF sin intervención manual cada ciclo.

### A1.2 Nivel de agua

| Qué | Detalle |
|-----|---------|
| Hardware | Sensor de nivel (prioridad: TOF / flotador / sonda mínima — decidir por línea) |
| Lógica | **No bombear en seco**; opcional: relleno / alerta si nivel bajo |
| API | Campo `nivel` (o equivalente) en sync/telemetría |
| UI | Lectura + alerta en monitoreo |

**Criterio de salida A1.2:** con depósito bajo, la bomba no arranca (o se apaga) y el panel muestra alerta clara.

### BOM mínimo A1 (por prototipo)

| Pieza | Uso |
|-------|-----|
| Kit A0 (ESP32 + relé + bomba + fuentes) | Base |
| Sensor de nivel (TOF10120 o flotador NC/NO) | Protección / telemetría nivel |
| Cableado estanco / soporte en depósito | Montaje |

Detalle BOM amplio: SSD `AVANCES_BOM_SMARTVEST_ECOGROW_2026-06-01.md` (sección EcoGrow).

### Aplicación por línea

| Línea | A1 tiempo | A1 nivel |
|-------|-----------|----------|
| Torre vegetal | Ciclo riego torre (ej. 15 min ON / 60 OFF — ajustar) | Depósito ~5 L; failsafe bomba seca |
| Forraje | Ciclo riego bandejas / germinación (tiempos distintos) | Depósito / tanque de riego forraje |

Los **tiempos ON/OFF** son parámetros de configuración, no hardcode de un solo cultivo.

---

## Fase A2 — Sensores de nutrientes y agua (después de A1)

**Objetivo:** telemetría real de calidad de solución.

| Sensor | Función |
|--------|---------|
| pH (ej. DFRobot SEN0161) | Acidez solución |
| EC / TDS (ej. SEN0244) | Conductividad / nutrientes |
| DS18B20 | Temperatura agua |
| (Opc.) calibración | Soluciones pH 4.0 / 7.0 |

Firmware completo: `platformio/esp32_hidroponico/` (hoy con drivers a completar).

**Criterio de salida:** lecturas reales en panel + alertas por rango de fase (perfiles existentes en `domain/hidroponia_torre.py`; perfiles forraje a documentar).

**No empezar A2** si A1.1 o A1.2 fallan en campo.

---

## Fase A3 — Ambiente y avanzado (posterior)

| Ítem | Notas |
|------|-------|
| T° / HR aire (DHT22 / BME280) | Ambiente invernadero / sala |
| Luz / DLI | Programa de iluminación |
| Recetas nutrientes A/B | Dosificación (actuadores extra) |
| IPM / calibración formal | Operación y mantenimiento |
| Modelo 3D torre / bandejas forraje | `hardware/3d/` |

---

## Mapa rápido: doc antigua vs nueva

La guía física `FASE1-ESP32-BOMBA-RELE.md` hablaba de:

| Antes | Ahora (este documento) |
|-------|-------------------------|
| “Fase 1” = relé + bomba | **A0** |
| “Fase 2” = todos los sensores | **A2** (nutrientes) — **después** de nivel |
| “Fase 3” = riego auto + nivel | **A1** — **prioridad actual** |

---

## Checklist de carga en repo (producto)

- [x] Visión dos líneas (`docs/producto/VISION-Y-LINEAS-ECOGROW.md`)
- [x] Este roadmap A0 → A1 → A2 → A3
- [ ] Firmware A1.1 estable en `main` (si hay cambios locales de riego auto → commit aparte)
- [ ] Integración sensor nivel (A1.2) — código + BOM confirmado
- [ ] Perfil dominio forraje (tiempos / setpoints) cuando haya prototipo físico listo

---

## Referencias

- [`FASE1-ESP32-BOMBA-RELE.md`](FASE1-ESP32-BOMBA-RELE.md) — cableado A0
- [`GUIA-ESP32-RELE.md`](GUIA-ESP32-RELE.md) — API
- [`../DOCUMENTACION-PROYECTO-ECOGROW.md`](../DOCUMENTACION-PROYECTO-ECOGROW.md) §16 Roadmap
- [`../hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`](../hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md)
