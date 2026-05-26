# Manual de dominio — Torre hidropónica vertical (EcoGrow)

Documento de referencia para producto, agronomía e ingeniería. Alinea el software con prácticas reales de **cultivo en columna** (lechugas, acelgas, espinacas, rúcula, albahaca).

> **Documentación técnica completa del proyecto:** [`docs/DOCUMENTACION-PROYECTO-ECOGROW.md`](../DOCUMENTACION-PROYECTO-ECOGROW.md)  
> **Presentación (tecnologías y arquitectura):** [`documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md`](../../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md)

---

## 1. Qué es una torre vertical en EcoGrow

| Concepto | En el sistema |
|----------|----------------|
| **Torre** | Unidad física con código único, depósito, bomba y sitios de planta en niveles |
| **Cultivo** | Variedad catalogada (ej. Lechuga Salanova Verde) |
| **Ciclo** | Instancia activa: torre + cultivo + **fase** + fechas |
| **Fase** | Etapa fenológica que define rangos pH/EC/riego (`domain/hidroponia_torre.py`) |
| **Lectura** | Telemetría IoT ligada al ciclo activo |
| **Actuador** | Bomba, válvulas, dosificador pH (estado en BD; hardware según despliegue) |

---

## 2. Mapa de cobertura del producto

### Cubierto hoy (software)

| Dominio | Función |
|---------|---------|
| Registro torre / usuario | Auth, códigos únicos |
| Catálogo 15 variedades | `DEFAULT_CULTIVOS` + formularios |
| Fases por variedad | `fases_cultivo`, selector en UI |
| Ciclo activo | Inicio, cambio de fase, cierre |
| Perfiles pH/EC por fase | `fetch_effective_control_configuration` |
| Sensores | pH, EC, T° agua/aire, HR, nivel, luz |
| Alertas | pH, EC, nivel crítico, T° agua |
| Control advisory | PID-fuzzy simplificado + eventos |
| IoT relé/bomba | `/api/iot/sync` |
| Agricultor IA | Recomendaciones + riego asistido |
| Reporte PDF cultivos | CRUD + export |
| Cosecha | `/torres/cultivo/cosecha`, tabla `eventos_cosecha` |
| Setpoints UI | `/torres/configuracion` |

### Roadmap (pendiente)

| Prioridad | Dominio | Descripción |
|-----------|---------|-------------|
| P2 | **Nutrientes** | Recetas A/B por fase, volúmenes dosificados |
| P2 | **Iluminación** | Fotoperiodo, DLI, actuador luz |
| P2 | **Torre física** | Niveles, copas por nivel, tipo NFT/aeropónico |
| P3 | **IPM** | Plagas, tratamientos, scouting |
| P3 | **Calibración** | Log sondas pH/EC, cambio de solución |
| P3 | **Germinador** | Bandeja antes de torre |

---

## 3. Fenología estándar (hoja verde en torre)

```text
Germinación → Plántula → Desarrollo foliar / Formación de bola → Cosecha
```

| Fase | Días ref. | pH | EC (mS/cm) | Notas clave |
|------|-----------|-----|------------|-------------|
| Germinación | 3 | 5.8–6.2 | 0.6–1.0 | Alta humedad, poca luz |
| Plántula | 7 | 5.6–6.2 | 0.8–1.2 | Trasplante a torre con 2–3 hojas verdaderas |
| Desarrollo foliar | 14 | 5.5–6.5 | 1.2–1.8 | Demanda N y Ca; oxígeno en raíz |
| Formación de bola | 10 | 5.5–6.4 | 1.2–1.9 | Evitar estrés térmico |
| Cosecha | 3 | 5.8–6.5 | 0.8–1.4 | Bajar EC 24–48 h antes mejora sabor |

Valores implementados en: `domain/hidroponia_torre.py` (`PHASE_PROFILES`).

---

## 4. Parámetros ambientales en torre

### Agua (solución nutritiva)

- **pH**: 5.5–6.5 mayoría hojas verdes; fuera de rango bloquea Fe, Mn, P.
- **EC**: sube con radiación y etapa; bajar antes de cosecha.
- **T° agua**: 18–22 °C ideal; >26 °C reduce O₂ disuelto → pudrición raíz.
- **Nivel depósito**: mínimo 20 % en software; objetivo 85 %; bomba protegida si bajo.

### Aire

- **T°**: 18–26 °C día; evitar >28 °C sostenido (espigamiento lechuga).
- **HR**: 50–70 %; >80 % favorece mildiu en hojas rizadas.
- **Luz**: registrar lux/PPFD; lechuga torre típico 12–16 h luz, DLI 12–17 mol/m²/d según variedad.

### Torre física (diseño)

- Módulos apilados 80 mm (config por defecto).
- Depósito 5 L referencia; bomba con altura manométrica ≤1.4 m.
- Aireación entre copas; drenaje continuo en NFT vertical.

---

## 5. Riego en columna

- **Ciclos cortos** en plántula (5 min ON / 30 OFF referencia).
- **Mayor frecuencia** en desarrollo foliar.
- **Nunca** bomba en seco: nivel + actuador `protegida`.
- ESP32 puede ejecutar relé según comando de `/api/iot/sync`.

---

## 6. Nutrición (guía, no automatizada aún)

| Elemento | Rol en torre |
|----------|----------------|
| N | Crecimiento foliar |
| P | Raíz temprana |
| K | Calidad y osmorregulación |
| Ca | Tip burn si falta con alta EC |
| Fe/Mn | Sensibles a pH >6.5 |

Acciones del motor de control: “Dosificar AB Mix”, “Diluir con agua”, “pH Up/Down” (advisory).

---

## 7. Flujo operativo recomendado (usuario)

1. Registrar torre y código para ESP32.
2. Crear cultivo en catálogo (o usar semilla).
3. **Gestionar fase** (`/torres/cultivo/fase`) — inicia o cambia ciclo.
4. Conectar ESP32 (relé primero, sensores después).
5. Monitoreo: comparar lecturas vs perfil de fase.
6. Agricultor IA para decisiones; autorizar con cuidado.
7. Cambiar fase al avanzar fenología.
8. **Registrar cosecha** (`/torres/cultivo/cosecha`) y limpiar torre.

---

## 8. Integración código ↔ agronomía

| Acción usuario | Código |
|----------------|--------|
| Cambiar fase | `update_active_cycle_phase` + `/torres/cultivo/fase` |
| Alertas pH/EC | `_record_control_state` + `fetch_effective_control_configuration` |
| Perfiles | `domain/hidroponia_torre.phase_profile_for` |
| IoT | `sync_iot_device`, firmware `platformio/esp32_rele_base` |

---

## 9. Calidad y seguridad alimentaria (orientación)

- Registrar fecha cambio de solución y calibración sondas.
- Agua de red: cloración previa si se recircula.
- Lavado de torre entre ciclos (hipoclorito / peróxido según protocolo del sitio).
- Trazabilidad: ciclo_id en cada lectura de sensor.

---

## 10. Cosecha y setpoints (UI)

| Acción | Ruta |
|--------|------|
| Registrar cosecha (cierra ciclo, bomba en reposo) | `/torres/cultivo/cosecha` |
| Editar pH/EC, nivel y riego ON/OFF | `/torres/configuracion` |

Tabla MySQL: `eventos_cosecha`. Funciones: `register_harvest`, `update_torre_control_configuration`, `update_torre_irrigation_schedule`.

---

*EcoGrow — dominio torre vertical v1.0 · Spec producto: `specs/002-dominio-hidroponia-torre/spec.md`*
