# Estructura del proyecto EcoGrow

Guía de organización del repositorio para desarrollo, revisión académica y entrega.

---

## Vista general

```text
proyecto_ecogrow/
│
├── app.py                 # Punto de entrada Flask
├── form.py                # Formularios (DTOs)
├── requirements.txt
├── render.yaml            # Despliegue Render
│
├── blueprints/            # Capa HTTP (rutas)
├── Conexión/              # Capa de datos (MySQL)
├── domain/                # Reglas agronómicas
├── models/                # Modelos de aplicación
├── services/              # Lógica de negocio
├── forms/                 # Reexportación de formularios
│
├── templates/             # Vistas Jinja2
├── static/                # CSS, imágenes, favicon
├── database/              # schema.sql
├── tests/                 # Pruebas unitarias
│
├── platformio/            # Firmware ESP32
├── hardware/              # Piezas físicas (CAD / impresión 3D)
│   └── 3d/
│       └── germinador/    # Estación de germinación (.3mf)
├── docs/                  # Documentación técnica
├── documentacion_equipo/  # Entregables y presentaciones
├── scripts/               # Utilidades (PDF, backup, IoT)
└── specs/                 # Especificaciones de producto
```

---

## Capas de software

| Capa | Carpeta | Responsabilidad |
|------|---------|-----------------|
| **Presentación** | `templates/`, `static/` | UI web |
| **Control** | `blueprints/` | Rutas, sesión, respuestas HTTP |
| **Validación** | `form.py`, `forms/` | Entrada de formularios |
| **Negocio** | `services/`, `domain/` | Cultivos, PDF, perfiles pH/EC |
| **Datos** | `Conexión/conexion.py` | SQL, IoT sync, alertas |
| **Persistencia** | MySQL | Tablas relacionales |
| **Embeddido** | `platformio/` | ESP32, relé, sensores |

### Flujo de una petición web

```text
Cliente → blueprint → form/service → Conexión → MySQL → template → HTML
```

### Flujo IoT

```text
ESP32 → POST /api/iot/sync → sensores blueprint → sync_iot_device → MySQL
      ← JSON comandos.rele_principal ←
```

---

## Blueprints (módulos HTTP)

| Archivo | Prefijo / rutas | Función |
|---------|-----------------|---------|
| `main.py` | `/`, `/about`, SEO | Páginas públicas |
| `auth.py` | `/login`, `/registro` | Autenticación |
| `torres.py` | `/torres`, `/dashboard` | Torres, ciclos, cosecha, config |
| `cultivos.py` | `/cultivos` | CRUD cultivos + PDF |
| `sensores.py` | `/sensores`, `/api/*` | Monitoreo e IoT |
| `ai.py` | `/agricultor-ia` | Asistente Gemini |
| `mysql.py` | `/mysql` | Admin BD (solo admin) |
| `shared.py` | — | CSRF, decoradores, seguridad |

---

## Dominio hidropónico

| Archivo | Contenido |
|---------|-----------|
| `domain/hidroponia_torre.py` | Perfiles pH/EC/riego por fase fenológica |
| `docs/producto/VISION-Y-LINEAS-ECOGROW.md` | Visión: 2 líneas (Plantas + Forraje) |
| `docs/iot/ROADMAP-AUTOMATIZACION-FASES.md` | Automatización A0→A1→A2→A3 |
| `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md` | Manual operativo |

---

## Base de datos (tablas clave)

| Tabla | Propósito |
|-------|-----------|
| `usuarios` | Cuentas |
| `torres` | Unidades físicas (`codigo_unico`) |
| `cultivos`, `fases_cultivo` | Catálogo |
| `ciclos_cultivo` | Ciclo activo por torre |
| `lecturas_sensores` | Telemetría |
| `configuracion_control` | Setpoints |
| `programaciones_riego` | ON/OFF |
| `actuadores_torre` | Bomba / relé |
| `eventos_cosecha` | Rendimiento |
| `alertas_sistema`, `eventos_control` | Operación |

Inicialización: `flask mysql-init` o `database/schema.sql`.

---

## Firmware (PlatformIO)

| Proyecto | Uso |
|----------|-----|
| `platformio/esp32_rele_base/` | **Fase 1:** WiFi + relé + bomba |
| `platformio/esp32_hidroponico/` | **Fase 2:** sensores completos |

Configuración local: `include/config.h` (no se sube a Git).

---

## Hardware 3D

| Carpeta | Contenido |
|---------|-----------|
| `hardware/3d/germinador/` | `estacion_germinacion_hidroponico.3mf` — estación de germinación (P3 dominio) |

Ver `hardware/3d/germinador/README.md` para slicer e integración con el flujo agronómico.

---

## Scripts útiles

| Script | Función |
|--------|---------|
| `scripts/generate_proyecto_pdf.py` | PDF documentación completa |
| `scripts/exportar_paquete_descargas.sh` | Paquete en ~/Downloads |
| `scripts/test-iot-sync.sh` | Probar API IoT |
| `scripts/esp32-setup-local.sh` | Generar config.h ESP32 |
| `scripts/db_backup.sh` / `db_restore.sh` | Respaldo MySQL local |

---

## Convenciones

- **Español** en UI, documentación y mensajes al usuario.
- **Snake_case** en Python; **blueprints** por dominio funcional.
- Secretos solo en variables de entorno (`.env`, Render), nunca en Git.
- Tests en `tests/` con `unittest`.

---

*EcoGrow — estructura v1.1*
