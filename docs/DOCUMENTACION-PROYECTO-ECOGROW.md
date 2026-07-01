# EcoGrow — Documentación completa del proyecto

**Versión del documento:** 2026-05-25  
**Repositorio:** https://github.com/elJohn72/proyecto_ecogrow  
**Tipo:** Aplicación web académica para gestión de hidroponía en torres verticales con IoT.

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Objetivos y alcance](#2-objetivos-y-alcance)
3. [Stack tecnológico](#3-stack-tecnológico)
4. [Arquitectura del sistema](#4-arquitectura-del-sistema)
5. [Estructura del repositorio](#5-estructura-del-repositorio)
6. [Flujo de datos y operación](#6-flujo-de-datos-y-operación)
7. [Módulos funcionales](#7-módulos-funcionales)
8. [Base de datos](#8-base-de-datos)
9. [API e IoT](#9-api-e-iot)
10. [Dominio hidropónico](#10-dominio-hidropónico)
11. [Seguridad y despliegue](#11-seguridad-y-despliegue)
12. [Variables de entorno](#12-variables-de-entorno)
13. [Instalación y ejecución](#13-instalación-y-ejecución)
14. [Pruebas y calidad](#14-pruebas-y-calidad)
15. [Documentación relacionada](#15-documentación-relacionada)
16. [Roadmap](#16-roadmap)

---

## 1. Resumen ejecutivo

**EcoGrow** es un sistema web que permite a un usuario (productor académico o equipo de laboratorio):

- Registrar **torres hidropónicas verticales** con código único para dispositivos IoT.
- Gestionar un **catálogo de cultivos** (variedades, fases fenológicas).
- Ejecutar **ciclos de cultivo** por torre (inicio, cambio de fase, cosecha, cierre).
- Recibir **telemetría** (pH, EC, temperatura, humedad, nivel, luz) desde ESP32.
- Controlar **actuadores** (bomba/relé) de forma manual o vía sincronización IoT.
- Obtener **alertas** cuando los parámetros salen del rango definido por fase y configuración.
- Usar un **asistente IA** (Google Gemini) para recomendaciones operativas.
- Exportar **reportes PDF** del catálogo de cultivos.

El proyecto integra **agronomía de torre vertical** (perfiles pH/EC por fase) con **ingeniería de software** en capas (Flask, MySQL, firmware embebido).

---

## 2. Objetivos y alcance

### Objetivos

| Objetivo | Cómo se cumple |
|----------|----------------|
| Gestión académica de cultivos | CRUD completo + PDF |
| Monitoreo en tiempo casi real | API de sensores + panel web |
| Automatización básica | Programación riego, relé IoT, motor de control advisory |
| Trazabilidad | Ciclos, lecturas ligadas a ciclo, eventos de control y cosecha |
| Experiencia de usuario clara | Dashboard, modos usuario/admin, plantillas Jinja2 |

### Alcance actual

- Multi-usuario con sesión (`Flask-Login`).
- Una **torre activa** por sesión (selector en `/torres`).
- Modo administrador restringido por correo (`ECOGROW_ADMIN_EMAILS`).
- Despliegue preparado en **Render** (`render.yaml` + Gunicorn).

### Fuera de alcance (por ahora)

- Dosificación automática de nutrientes en hardware.
- Control de iluminación LED integrado en BD.
- App móvil nativa.
- Multi-tenant comercial.

---

## 3. Stack tecnológico

### Backend y aplicación web

| Tecnología | Versión (requirements) | Uso |
|------------|------------------------|-----|
| **Python** | 3.x | Lenguaje principal |
| **Flask** | 3.1.2 | Framework web, rutas, blueprints |
| **Flask-Login** | 0.6.3 | Sesiones y autenticación |
| **Jinja2** | 3.1.6 | Plantillas HTML |
| **mysql-connector-python** | 9.6.0 | Acceso a MySQL/MariaDB |
| **Gunicorn** | 21.2.0 | Servidor WSGI en producción |
| **Werkzeug** | 3.1.5 | Utilidades HTTP (dependencia Flask) |
| **fpdf2** | 2.8.3 | Generación de reportes PDF |
| **google-generativeai** | 0.8.3 | Agricultor IA (Gemini) |

### Frontend

| Tecnología | Uso |
|------------|-----|
| **HTML5** | Estructura de páginas |
| **CSS propio** (`static/style.css`) | Diseño del panel (métricas, tablas, formularios) |
| **Bootstrap 5** (CDN) | Componentes base en algunas vistas |
| **JavaScript** (inline/ligero) | Selectores dinámicos (fases por cultivo), chat IA |

### Base de datos

| Tecnología | Uso |
|------------|-----|
| **MySQL / MariaDB** | Persistencia relacional |
| **Schema SQL** | `database/schema.sql` + migración implícita en `create_mysql_tables()` |

### IoT y embebidos

| Tecnología | Uso |
|------------|-----|
| **ESP32** | Microcontrolador WiFi |
| **PlatformIO** | Build y upload de firmware |
| **Arduino framework** | `platformio/esp32_rele_base`, `platformio/esp32_hidroponico` |
| **HTTP/JSON** | Comunicación con `/api/iot/sync` y `/api/sensores/lectura` |

### DevOps y calidad

| Herramienta | Uso |
|-------------|-----|
| **Render** | Hosting web (`render.yaml`) |
| **Git / GitHub** | Control de versiones |
| **unittest** | Pruebas en `tests/test_app.py` |
| **Spec Kit** | Especificaciones en `specs/` |
| **Squirrelscan** (opcional) | Auditoría web local (`scripts/audit-local.sh`) |

---

## 4. Arquitectura del sistema

### Diagrama lógico

```text
                    ┌─────────────────────────────────────┐
                    │           Navegador web              │
                    │  (Jinja2 + CSS + JS ligero)          │
                    └─────────────────┬───────────────────┘
                                      │ HTTPS
                    ┌─────────────────▼───────────────────┐
                    │         Flask (app.py)                 │
                    │  ┌─────────┬─────────┬──────────────┐  │
                    │  │ auth    │ torres  │ cultivos     │  │
                    │  │ sensores│ ai      │ main/mysql   │  │
                    │  └────┬────┴────┬────┴──────┬───────┘  │
                    │       │ forms │ services │ models     │
                    └───────┼───────┼──────────┼────────────┘
                            │       │          │
              ┌─────────────▼───────▼──────────▼─────────────┐
              │         Conexión/conexion.py                  │
              │  (SQL, tablas, control, IoT sync)             │
              └─────────────┬────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │    MySQL / MariaDB         │
              └─────────────▲─────────────┘
                            │ JSON + token
              ┌─────────────┴─────────────┐
              │   ESP32 (PlatformIO)       │
              │   relé / sensores          │
              └───────────────────────────┘
```

### Capas de código

| Capa | Ubicación | Responsabilidad |
|------|-----------|-----------------|
| **Presentación** | `templates/`, `static/` | UI, formularios, dashboard |
| **Controladores** | `blueprints/*.py` | Rutas HTTP, validación de entrada, flashes |
| **Formularios** | `form.py`, `forms/` | DTOs de formulario (`*FormData`) |
| **Servicios** | `services/` | Lógica de cultivos, PDF |
| **Modelos** | `models/` | `User`, wrappers de dominio |
| **Dominio agronómico** | `domain/hidroponia_torre.py` | Perfiles pH/EC/riego por fase |
| **Acceso a datos** | `Conexión/conexion.py` | SQL, transacciones, IoT, alertas |
| **Firmware** | `platformio/` | Hardware ESP32 |

### Punto de entrada

- **`app.py`**: crea `Flask`, configura `LoginManager`, registra blueprints, `/health`, headers de seguridad, comando `flask mysql-init`.

---

## 5. Estructura del repositorio

```text
proyecto_ecogrow/
├── app.py                      # Aplicación Flask
├── form.py                     # Formularios principales
├── requirements.txt
├── render.yaml                 # Despliegue Render
├── README.md
├── blueprints/                 # Rutas por módulo
│   ├── auth.py
│   ├── main.py
│   ├── torres.py
│   ├── cultivos.py
│   ├── sensores.py
│   ├── mysql.py
│   ├── ai.py
│   └── shared.py               # Decoradores, CSRF, seguridad
├── Conexión/
│   ├── __init__.py             # Reexporta funciones públicas
│   └── conexion.py             # Capa de datos (~2000 líneas)
├── domain/
│   └── hidroponia_torre.py     # Perfiles agronómicos
├── models/
├── services/
├── forms/
├── templates/
├── static/
├── tests/
├── database/schema.sql
├── platformio/
│   ├── esp32_rele_base/        # Firmware mínimo relé
│   └── esp32_hidroponico/      # Firmware sensores completo
├── docs/
│   ├── DOCUMENTACION-PROYECTO-ECOGROW.md   # Este archivo
│   ├── hidroponia/
│   ├── iot/
│   └── auditoria/
├── documentacion_equipo/
│   └── presentaciones/         # Material para sustentación
└── specs/                      # Spec-driven development
```

---

## 6. Flujo de datos y operación

### 6.1 Registro e inicio de sesión

1. Usuario se registra en `/registro` o inicia sesión en `/login`.
2. `Flask-Login` guarda `id_usuario` en sesión.
3. Si no hay torre activa, redirige a `/torres` para registrar o seleccionar torre.
4. `session["torre_id"]` define la torre de trabajo.

### 6.2 Ciclo de cultivo

```text
Registrar torre → Crear/seleccionar cultivo → Gestionar fase (/torres/cultivo/fase)
       → Telemetría (requiere ciclo activo) → Cambiar fase según fenología
       → Registrar cosecha (/torres/cultivo/cosecha) → Ciclo cerrado, bomba reposo
```

### 6.3 Telemetría IoT

1. ESP32 envía `POST /api/sensores/lectura` o `POST /api/iot/sync` con header `X-API-Token`.
2. Servidor valida token (`ECOGROW_SENSOR_API_TOKEN`).
3. Resuelve torre por `torre_codigo` o `torre_id`.
4. Inserta lectura en `lecturas_sensores` (si hay ciclo activo para sensores completos).
5. Evalúa setpoints (`fetch_effective_control_configuration`) y genera alertas/eventos.
6. Devuelve comandos (ej. estado del relé) al dispositivo.

### 6.4 Configuración efectiva (pH/EC)

La configuración que usa el motor de control combina:

- **Setpoints de torre** (`configuracion_control`, editable en `/torres/configuracion`).
- **Perfil de fase** del ciclo activo (`domain/hidroponia_torre.py`).

Función clave: `fetch_effective_control_configuration(torre_id)`.

---

## 7. Módulos funcionales

### 7.1 Autenticación (`blueprints/auth.py`)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/login` | GET/POST | Inicio de sesión |
| `/registro` | GET/POST | Alta de usuario |
| `/logout` | GET | Cierre de sesión |

### 7.2 Páginas públicas (`blueprints/main.py`)

| Ruta | Descripción |
|------|-------------|
| `/` | Landing |
| `/about`, `/contactos`, `/demo`, `/privacidad` | Información |
| `/robots.txt`, `/sitemap.xml` | SEO |
| `/modo/admin` o `/modo/user` | Cambio de UI (solo admin autorizado) |
| `/health` | Health check JSON |

### 7.3 Torres y panel (`blueprints/torres.py`)

| Ruta | Descripción |
|------|-------------|
| `/torres` | Listado y registro |
| `/torres/seleccionar/<id>` | Torre activa en sesión |
| `/dashboard` | Panel principal |
| `/torres/cultivo/fase` | Inicio/cambio de fase |
| `/torres/cultivo/cosecha` | Registro de cosecha |
| `/torres/configuracion` | Setpoints y riego |
| `/torres/cultivo/finalizar` | Cierre sin cosecha |

### 7.4 Cultivos (`blueprints/cultivos.py`)

| Ruta | Descripción |
|------|-------------|
| `/cultivos` | Listado |
| `/cultivos/nuevo`, `/editar/<id>` | CRUD |
| `/cultivos/borrar/<id>` | Eliminación |
| `/cultivos/inactivos` | Archivo |
| `/cultivos/reporte/pdf` | Export PDF |

### 7.5 Sensores e IoT (`blueprints/sensores.py`)

| Ruta | Descripción |
|------|-------------|
| `/sensores` | Monitoreo web |
| `/irrigation` | Panel de riego |
| `/monitoreo/rele/<torre_id>` | Control manual relé |
| `/api/sensores/lectura` | API telemetría |
| `/api/iot/sync` | Sync relé + opcional sensores |

### 7.6 Administración MySQL (`blueprints/mysql.py`)

| Ruta | Descripción |
|------|-------------|
| `/mysql` | Panel admin |
| `/mysql/usuarios` | CRUD usuarios BD |

Requiere modo admin y correo en `ECOGROW_ADMIN_EMAILS`.

### 7.7 Agricultor IA (`blueprints/ai.py`)

| Ruta | Descripción |
|------|-------------|
| `/agricultor-ia` | Chat UI |
| `/api/agricultor-ia/chat` | API conversación |
| `/api/ai_advice/<torre_id>` | Consejo por torre |

Usa contexto de torre, última lectura y configuración efectiva.

---

## 8. Base de datos

### Tablas principales

| Tabla | Propósito |
|-------|-----------|
| `usuarios` | Cuentas de acceso |
| `torres` | Unidades físicas (`codigo_unico`) |
| `cultivos` | Catálogo de variedades |
| `fases_cultivo` | Etapas permitidas por cultivo |
| `ciclos_cultivo` | Instancias activas/históricas |
| `lecturas_sensores` | Telemetría |
| `configuracion_control` | Setpoints por torre |
| `programaciones_riego` | ON/OFF, estrategia |
| `actuadores_torre` | Bomba, relé, modos |
| `alertas_sistema` | Alertas activas |
| `eventos_control` | Historial decisiones |
| `eventos_cosecha` | Peso, plantas, trazabilidad |

### Inicialización

```bash
flask mysql-init
```

O importar `database/schema.sql` en MySQL.

### Sincronización entre dos PCs

- **Código:** Git/GitHub.
- **Datos:** misma BD remota **o** `scripts/db_backup.sh` / `scripts/db_restore.sh` (respaldos en `backups/`, ignorados por Git).

---

## 9. API e IoT

### Autenticación de dispositivos

Todas las rutas API exigen:

```http
X-API-Token: <ECOGROW_SENSOR_API_TOKEN>
```

### POST `/api/sensores/lectura`

Campos típicos: `torre_codigo`, `dispositivo`, `ph`, `ec`, `temperatura_agua`, `temperatura_aire`, `humedad`, `nivel`, `luz`, etc.

**Nota:** requiere **ciclo activo** en la torre para persistir la lectura.

### POST `/api/iot/sync`

Pensado para ESP32 con relé:

- Identifica torre por código.
- Actualiza estado de actuador.
- Opcionalmente recibe lecturas.
- Responde `comandos.rele_principal` (`encendido` / `apagado`).

Documentación detallada: [`docs/iot/GUIA-ESP32-RELE.md`](iot/GUIA-ESP32-RELE.md).

### Firmware

| Carpeta | Nivel |
|---------|--------|
| `platformio/esp32_rele_base/` | WiFi + relé + sync (recomendado para empezar) |
| `platformio/esp32_hidroponico/` | Sensores + riego (completo) |

---

## 10. Dominio hidropónico

La lógica agronómica de **torre vertical** está centralizada en:

- **`domain/hidroponia_torre.py`**: `PHASE_PROFILES`, `DEFAULT_LEAFY_PROFILE`, `CONTROL_DEFAULTS`.
- **Manual operativo:** [`docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`](hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md).

### Conceptos

| Término | Significado en EcoGrow |
|---------|------------------------|
| Torre | Unidad con depósito, bomba, niveles de planta |
| Cultivo | Variedad en catálogo |
| Ciclo | Torre + cultivo + fase + fechas |
| Fase | Etapa fenológica (afecta pH/EC objetivo) |
| Cosecha | Evento que cierra ciclo y registra rendimiento |

### Parámetros de referencia (hoja verde)

- pH: **5.5–6.5**
- EC: según fase (0.6–2.4 mS/cm)
- T° agua: **18–24 °C**
- Riego: ciclos cortos ON/OFF (ej. 15 min / 60 min)

---

## 11. Seguridad y despliegue

### Medidas en aplicación

- `SECRET_KEY` para sesiones firmadas.
- Cookies `HttpOnly`, `SameSite`, `Secure` en producción.
- Protección **CSRF** en formularios POST.
- Headers: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, **CSP Report-Only**.
- Modo admin solo por lista de correos (no solo por sesión manipulada).
- Token de API separado para dispositivos IoT.

### Despliegue en Render

Archivo `render.yaml`:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Variables: `MYSQL_*`, `SECRET_KEY`, `ECOGROW_SENSOR_API_TOKEN`, `ECOGROW_ADMIN_EMAILS`, `SESSION_COOKIE_SECURE=true`

Checklist producción: [`docs/auditoria/CHECKLIST-PRODUCCION.md`](auditoria/CHECKLIST-PRODUCCION.md).

---

## 12. Variables de entorno

```env
# Flask / sesión
SECRET_KEY=...
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=ecogrow_mysql
MYSQL_UNIX_SOCKET=/ruta/al/socket
MYSQL_USE_SOCKET=true
MYSQL_AUTO_CREATE_DATABASE=true
MYSQL_SSL_DISABLED=true

# IoT y admin
ECOGROW_SENSOR_API_TOKEN=token-secreto-dispositivo
ECOGROW_ADMIN_EMAILS=admin@correo.com,otro@correo.com

# IA (opcional en local)
GOOGLE_API_KEY=...
```

---

## 13. Instalación y ejecución

```bash
git clone https://github.com/elJohn72/proyecto_ecogrow.git
cd proyecto_ecogrow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar variables MYSQL_* y SECRET_KEY
flask mysql-init
flask run
```

Producción local con Gunicorn:

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

---

## 14. Pruebas y calidad

```bash
python3 -m unittest discover -s tests -v
```

Cobertura actual (19 tests): rutas públicas, login, CSRF, APIs IoT/sensores, permisos admin, formularios de cosecha y configuración.

Auditoría web opcional:

```bash
bash scripts/audit-local.sh
```

---

## 15. Documentación relacionada

| Documento | Contenido |
|-----------|-----------|
| [`README.md`](../README.md) | Inicio rápido |
| [`docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`](hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md) | Agronomía torre vertical |
| [`docs/iot/GUIA-ESP32-RELE.md`](iot/GUIA-ESP32-RELE.md) | Firmware y API relé |
| [`docs/auditoria/INFORME-AUDITORIA-TOTAL.md`](auditoria/INFORME-AUDITORIA-TOTAL.md) | Auditoría web |
| [`documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md`](../documentacion_equipo/presentaciones/ECOGROW-TECNOLOGIAS-Y-ARQUITECTURA.md) | Presentación para sustentación |
| [`specs/001-auditoria-web/`](../specs/001-auditoria-web/) | Spec remediación web |
| [`specs/002-dominio-hidroponia-torre/`](../specs/002-dominio-hidroponia-torre/) | Spec dominio hidropónico |

---

## 16. Roadmap

| Prioridad | Funcionalidad | Estado |
|-----------|---------------|--------|
| P0 | Auth, torres, cultivos CRUD, sensores, PDF | Hecho |
| P0 | IoT relé `/api/iot/sync` | Hecho |
| P1 | Perfiles pH/EC por fase | Hecho |
| P1 | Cosecha (`eventos_cosecha`) | Hecho |
| P1 | Edición setpoints UI | Hecho |
| P2 | Recetas nutrientes A/B | Pendiente |
| P2 | Programa de luz / DLI | Pendiente |
| P2 | Modelo físico torre (niveles, copas) | Pendiente |
| P3 | Modelo 3D germinador (`.3mf`) | Hecho — `hardware/3d/germinador/` |
| P3 | IPM, calibración sondas, operación germinador | Pendiente |

---

*Documento mantenido por el equipo EcoGrow. Para cambios de producto, actualizar este archivo y el manual de dominio en la misma entrega.*
