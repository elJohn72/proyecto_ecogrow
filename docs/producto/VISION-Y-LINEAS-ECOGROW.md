# EcoGrow — visión de producto y líneas de negocio

**Estado:** vigente (John, 2026-07-13)  
**Repo:** https://github.com/elJohn72/proyecto_ecogrow  
**Marca:** EcoGrow (no “Cobrogg” / Ecogrok / ECOGROCK)

---

## 1. Qué es EcoGrow

**EcoGrow** es la línea de **AJTecnology / AJENZA** orientada a la **automatización de procesos agrícolas** con hidroponía e IoT.

No es solo un prototipo académico: es la base de una **empresa/producto** que desarrolla prototipos y sistemas para:

1. Cultivo hidropónico de **hortalizas / vegetales** en torre vertical.
2. Producción de **forraje hidropónico** para animales.

El software, firmware y hardware del repo sirven a **ambas líneas**, con perfiles y parámetros por tipo de sistema.

---

## 2. Dos líneas de producto

| Línea | Nombre corto | Qué produce | Público / uso |
|-------|--------------|-------------|---------------|
| **A — Torre vegetal** | EcoGrow Plantas | Lechuga, berro, cilantro, hierbas y hortalizas de hoja en **torres verticales** | Laboratorio, club, demo, productores urbanos, competencia |
| **B — Forraje hidropónico** | EcoGrow Ganadero / Forraje | Forraje verde hidropónico / aeropónico para **vacas, cerdos, aves** y otros animales que consumen este sistema | Finca, ganadería, demo Agrotech |

### 2.1 Línea A — Torre vertical (vegetales)

- Sistema ya documentado en `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`.
- Panel web: torres, ciclos, fases fenológicas, riego, telemetría.
- Hardware físico: torre + depósito + bomba + (próximo) nivel de agua.
- Germinador 3D: `hardware/3d/germinador/`.

Cultivos de referencia (no lista cerrada): lechuga, berro, cilantro / hierbas de hoja, otros de ciclo corto en NFT / torre.

### 2.2 Línea B — Forraje hidropónico (animales)

- Misma filosofía de **automatización** (bomba, nivel, luego nutrientes).
- Diferencias típicas vs torre vegetal: bandejas / germinación de grano, ciclos más cortos, densidades distintas, a veces sin torre apilada.
- Prototipos y mejoras físicas (estructura, germinación) pueden vivir en carpetas de hardware/forraje cuando se agreguen modelos.

> Relación con otros prototipos del club (p. ej. Cuby / forraje): pueden compartir sensores, firmware y panel EcoGrow; la marca comercial de automatización agrícola bajo AJTecnology es **EcoGrow**.

---

## 3. Principio de desarrollo

**Automatizar poco a poco, por fases.**  
No meter pH/EC/nutrientes hasta que bomba + tiempo + nivel estén estables en banco y en torre/forraje.

Ver roadmap operativo: [`../iot/ROADMAP-AUTOMATIZACION-FASES.md`](../iot/ROADMAP-AUTOMATIZACION-FASES.md).

---

## 4. Qué vive en este repositorio

| Capa | Contenido |
|------|-----------|
| **Producto** | Esta visión, roadmap de automatización |
| **Software** | Flask, MySQL, API IoT, riego, alertas |
| **Firmware** | ESP32 relé (fase actual) → nivel → sensores nutrientes |
| **Hardware 3D** | Germinador; torre/forraje pendientes |
| **Docs agronómicas** | Manual torre; futuros perfiles forraje |

Repo visual / landing: https://github.com/elJohn72/Ecogrow.io (complementario).

---

## 5. Decisiones explícitas (John)

| Fecha | Decisión |
|-------|----------|
| 2026-07-13 | EcoGrow = automatización agrícola; **dos líneas**: torre vegetal + forraje animales |
| 2026-07-13 | Automatización **por fases**: primero bomba por tiempo + nivel de agua; después sensores de nutrientes |
| 2026-07-13 | Seguir desarrollando más prototipos sin mezclar alcance: no saltar a nutrientes antes de A1 |

---

## 6. Relación con AJTecnology

- Línea **Agrotech / IoT** del Club de Robótica.
- Alineado a cursos M3 (ESP32, sensores, automatización).
- Competencia / demos: priorizar puesta a punto de **bomba + nivel** en la línea que se exhiba.

Ficha SSD: `01_Unidades/AJTecnology/Club_Robotica_AJTecnology/ECOGROW_FICHA.md`
