# EcoGrow — Presentación: tecnologías, arquitectura y funcionamiento

**Uso sugerido:** sustentación académica, defensa de proyecto o onboarding del equipo.  
**Duración estimada:** 15–25 minutos (20 diapositivas).

---

## Diapositiva 1 — Título

# EcoGrow
### Sistema web de gestión hidropónica en torres verticales con IoT

- Repositorio: https://github.com/elJohn72/proyecto_ecogrow
- Stack: Python · Flask · MySQL · ESP32
- Documentación completa: `docs/DOCUMENTACION-PROYECTO-ECOGROW.md`

---

## Diapositiva 2 — Problema

### Contexto

- La hidroponía en **torre vertical** exige control de pH, EC, riego y trazabilidad.
- En laboratorio o piloto académico hace falta un **panel central** y datos históricos.
- Los sensores y actuadores deben integrarse sin exponer la base de datos.

### Propuesta EcoGrow

Una aplicación web que une **agronomía**, **software** y **hardware IoT** en un solo flujo operativo.

---

## Diapositiva 3 — Objetivos del proyecto

| Objetivo | Entregable |
|----------|------------|
| Gestionar cultivos | CRUD + reporte PDF |
| Gestionar torres | Registro, ciclo activo, cosecha |
| Monitorear variables | Panel + API REST |
| Automatizar riego básico | Programación ON/OFF + relé ESP32 |
| Asistir al operador | Agricultor IA (Gemini) |
| Cumplir consigna académica | Flask + MySQL + evidencias |

---

## Diapositiva 4 — Stack tecnológico (resumen)

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Frontend   │   │   Backend    │   │   Datos      │
│ HTML/Jinja2  │   │ Flask 3.x    │   │ MySQL        │
│ CSS + Bootstrap│ │ Flask-Login  │   │ MariaDB      │
└──────────────┘   │ Gunicorn     │   └──────────────┘
                   │ fpdf2, Gemini│
                   └──────┬───────┘
                          │
                   ┌──────▼───────┐
                   │ ESP32 + WiFi │
                   │ PlatformIO   │
                   └──────────────┘
```

---

## Diapositiva 5 — Backend (Python / Flask)

| Componente | Función |
|------------|---------|
| **Flask** | Servidor web, rutas, JSON |
| **Blueprints** | Módulos: auth, torres, cultivos, sensores, ai, mysql |
| **Flask-Login** | Sesión de usuario |
| **form.py / forms/** | Validación de formularios |
| **services/** | PDF y lógica de cultivos |
| **Conexión/conexion.py** | Acceso SQL unificado |

**Por qué Flask:** ligero, ideal para proyectos académicos, fácil de desplegar en Render.

---

## Diapositiva 6 — Frontend

| Tecnología | Rol |
|------------|-----|
| **Jinja2** | Plantillas dinámicas (`templates/`) |
| **CSS propio** | Identidad visual del panel |
| **Bootstrap 5** | Grillas y componentes en vistas públicas |
| **JavaScript** | Fases por cultivo, chat IA |

No hay SPA (React/Vue): arquitectura **server-rendered**, simple de mantener y desplegar.

---

## Diapositiva 7 — Base de datos (MySQL)

### Entidades clave

- **usuarios** → autenticación
- **torres** → `codigo_unico` para IoT
- **cultivos** + **fases_cultivo** → catálogo agronómico
- **ciclos_cultivo** → qué crece ahora en cada torre
- **lecturas_sensores** → telemetría
- **configuracion_control** + **programaciones_riego** → setpoints
- **eventos_cosecha** → rendimiento y cierre de ciclo

Inicialización: `flask mysql-init` o `database/schema.sql`.

---

## Diapositiva 8 — Arquitectura en capas

```text
Usuario → Blueprint (HTTP) → FormData / Services
                ↓
         conexion.py (SQL)
                ↓
            MySQL
                ↑
         ESP32 (API token)
```

**Separación de responsabilidades:** las plantillas no ejecutan SQL; la lógica agronómica vive en `domain/hidroponia_torre.py`.

---

## Diapositiva 9 — Cómo funciona: flujo del usuario

1. **Registro / login**
2. **Registrar o elegir torre** (`/torres`)
3. **Definir cultivo y fase** (`/torres/cultivo/fase`)
4. **Conectar ESP32** con código de torre
5. **Monitorear** (`/sensores`, `/irrigation`)
6. **Ajustar setpoints** (`/torres/configuracion`)
7. **Registrar cosecha** (`/torres/cultivo/cosecha`) → ciclo cerrado

---

## Diapositiva 10 — Dominio hidropónico (torre vertical)

| Fase | pH ref. | EC ref. (mS/cm) |
|------|---------|-----------------|
| Germinación | 5.8–6.2 | 0.6–1.0 |
| Plántula | 5.6–6.2 | 0.8–1.2 |
| Desarrollo foliar | 5.5–6.5 | 1.2–1.8 |
| Formación de bola | 5.5–6.4 | 1.2–1.9 |
| Cosecha | 5.8–6.5 | 0.8–1.4 |

Implementado en `domain/hidroponia_torre.py` y fusionado con setpoints de torre en runtime.

---

## Diapositiva 11 — Motor de control (advisory)

- Compara lecturas vs **configuración efectiva** (torre + fase).
- Genera **alertas** (pH, EC, nivel crítico, temperatura agua).
- Registra **eventos_control** (decisiones sugeridas).
- **No sustituye** al operador en dosificación química (aún manual/advisory).

Protección de bomba: nivel bajo → actuador en modo protegido.

---

## Diapositiva 12 — IoT: ESP32 y APIs

### Dos endpoints principales

| Endpoint | Uso |
|----------|-----|
| `POST /api/sensores/lectura` | Telemetría completa |
| `POST /api/iot/sync` | Relé + sync simplificado |

### Seguridad

Header obligatorio: `X-API-Token: ECOGROW_SENSOR_API_TOKEN`

### Firmware

- **esp32_rele_base** — empezar aquí (WiFi + relé)
- **esp32_hidroponico** — sensores + riego avanzado

---

## Diapositiva 13 — Diagrama de secuencia IoT

```text
ESP32                    Flask API                 MySQL
  | POST /api/iot/sync      |                        |
  |------------------------>| validar token          |
  |                         | resolver torre         |
  |                         | actualizar actuador    |
  |                         |----------------------->|
  |                         | evaluar alertas        |
  |<------------------------| JSON comandos relé     |
  | ejecuta relé            |                        |
```

---

## Diapositiva 14 — Agricultor IA

| Elemento | Detalle |
|----------|---------|
| Proveedor | Google Generative AI (Gemini) |
| Ruta UI | `/agricultor-ia` |
| Contexto | Torre activa, última lectura, setpoints |
| Acciones | Puede sugerir riego; el usuario autoriza |

Variable: `GOOGLE_API_KEY` en entorno de despliegue.

---

## Diapositiva 15 — Seguridad

- Sesiones firmadas (`SECRET_KEY`)
- CSRF en formularios
- Cookies seguras en producción (`SESSION_COOKIE_SECURE`)
- Headers HTTP de endurecimiento
- Admin solo por lista de correos (`ECOGROW_ADMIN_EMAILS`)
- Token separado para dispositivos IoT

---

## Diapositiva 16 — Despliegue (Render)

```yaml
# render.yaml (resumen)
buildCommand: pip install -r requirements.txt
startCommand: gunicorn app:app
```

Variables críticas en cloud: `MYSQL_*`, `SECRET_KEY`, `ECOGROW_SENSOR_API_TOKEN`, `ECOGROW_ADMIN_EMAILS`.

Health check: `GET /health` → `{"status":"ok"}`.

---

## Diapositiva 17 — Pruebas y calidad

```bash
python3 -m unittest discover -s tests -v
```

**19 pruebas** cubren: rutas públicas, login, APIs, permisos admin, formularios nuevos.

Auditoría web opcional con Squirrelscan (`docs/auditoria/`).

---

## Diapositiva 18 — Estructura del equipo / entregables

| Carpeta | Contenido |
|---------|-----------|
| `docs/` | Documentación técnica y agronómica |
| `documentacion_equipo/` | PDFs, presentaciones, esquemáticos |
| `specs/` | Especificaciones Spec Kit |
| `platformio/` | Firmware |
| `tests/` | Pruebas automatizadas |

**Entrega académica típica:** repo GitHub + demo en vivo + PDF cultivos + este material de sustentación.

---

## Diapositiva 19 — Logros recientes

- Perfiles pH/EC por fase integrados al monitoreo
- API IoT para relé ESP32
- Registro de **cosecha** con cierre de ciclo
- UI de **setpoints** (pH, EC, riego ON/OFF)
- SEO: robots, sitemap, privacidad
- Modo admin endurecido

---

## Diapositiva 20 — Cierre y próximos pasos

### Preguntas frecuentes

- **¿Por qué MySQL?** Relaciones claras, requisito académico, despliegue en Render.
- **¿Funciona sin internet?** El panel necesita servidor; ESP32 necesita WiFi al API.
- **¿Qué falta?** Recetas nutrientes, luz, modelo físico de niveles.

### Contacto / repo

https://github.com/elJohn72/proyecto_ecogrow

**Gracias.**

---

## Notas para el expositor

- Demo sugerida: login → seleccionar torre → dashboard → monitoreo → (opcional) Postman a `/api/iot/sync`.
- Si preguntan por agronomía, abrir `docs/hidroponia/MANUAL-DOMINIO-TORRE-VERTICAL.md`.
- Si preguntan por código, mostrar `blueprints/torres.py` y `Conexión/conexion.py` (funciones `register_harvest`, `sync_iot_device`).
