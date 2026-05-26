# Feature Specification: Dominio hidroponía torre vertical

**Created**: 2026-05-26  
**Status**: In progress (núcleo agronómico v1 implementado)

## Objetivo

Que EcoGrow sea un producto **completo y creíble** para operación de torres hidropónicas verticales: desde germinación hasta cosecha, con telemetría, alertas por fase y actuación IoT escalable.

## User Stories

### P1 — Fase con rangos agronómicos (implementado v1)

**Given** torre con ciclo activo en fase "plantula", **When** llega lectura pH 7.0, **Then** alerta crítica usando rango 5.6–6.2 de esa fase (no rango genérico incorrecto).

### P1 — Cambio de fase operativo (implementado v1)

**Given** cultivo activo, **When** usuario guarda nueva fase en `/torres/cultivo/fase`, **Then** `ciclos_cultivo.fase` y `cultivos.estado` se actualizan y el monitoreo muestra nuevo perfil.

### P2 — Cosecha con trazabilidad (pendiente)

**Given** fase cosecha, **When** usuario registra cosecha, **Then** se guardan peso/fecha, se cierra ciclo y se archiva historial.

### P2 — Recetas nutricionales (pendiente)

**Given** fase desarrollo foliar, **When** sistema recomienda dosificar, **Then** muestra ml de A/B según receta y volumen de depósito.

## Referencias

- Manual: `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`
- Perfiles código: `domain/hidroponia_torre.py`
- IoT relé: `docs/iot/GUIA-ESP32-RELE.md`
