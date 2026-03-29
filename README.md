# EcoGrow

Aplicacion web academica desarrollada con Flask para gestionar un sistema hidropónico con enfoque en monitoreo, telemetria IoT, gestion de torres y CRUD de cultivos sobre MySQL/MariaDB.

## Estado actual

Esta version del proyecto cumple con:

- autenticacion de usuarios con `Flask-Login`
- CRUD completo de `cultivos`
- gestion de usuarios en MySQL/MariaDB
- monitoreo de sensores por torre
- plantillas con Jinja2
- estilos con Bootstrap y CSS propio
- generacion de reportes PDF de cultivos
- estructura organizada en capas: `models`, `services`, `forms`, `conexion`

## Tecnologias

- Python 3
- Flask
- Flask-Login
- MySQL Connector for Python
- MySQL / MariaDB
- Jinja2
- Bootstrap 5
- HTML + CSS
- fpdf2
- PlatformIO + ESP32

## Estructura principal

```text
proyecto_ecogrow/
├── app.py
├── form.py
├── requirements.txt
├── render.yaml
├── README.md
├── blueprints/
│   ├── auth.py
│   ├── cultivos.py
│   ├── main.py
│   ├── mysql.py
│   ├── sensores.py
│   ├── shared.py
│   ├── torres.py
│   └── ai.py
├── conexion/
│   ├── __init__.py
│   └── conexion.py
├── Conexión/
│   ├── __init__.py
│   └── conexion.py
├── models/
│   ├── __init__.py
│   ├── cultivo.py
│   └── user.py
├── services/
│   ├── __init__.py
│   └── cultivo_service.py
├── forms/
│   ├── __init__.py
│   ├── cultivo_form.py
│   ├── login_form.py
│   ├── torre_form.py
│   └── usuario_form.py
├── database/
│   └── schema.sql
├── templates/
│   ├── base.html
│   ├── cultivos/
│   │   ├── form.html
│   │   └── lista.html
│   └── ...
├── static/
├── tests/
│   └── test_app.py
└── platformio/
```

## Arquitectura

- `app.py`: crea la aplicacion Flask, inicializa `Flask-Login`, registra blueprints y comandos CLI.
- `conexion/conexion.py`: capa de compatibilidad para la conexion principal a MySQL/MariaDB.
- `models/`: modelos del sistema usados por la aplicacion.
- `services/`: servicios con logica de negocio y generacion de reportes.
- `forms/`: acceso organizado a los formularios del sistema.
- `blueprints/auth.py`: login, registro y logout.
- `blueprints/torres.py`: gestion de torres y panel principal.
- `blueprints/cultivos.py`: CRUD completo de cultivos y reporte PDF.
- `blueprints/sensores.py`: monitoreo y recepcion de lecturas IoT.
- `blueprints/mysql.py`: gestion de usuarios en MySQL/MariaDB.
- `Conexión/conexion.py`: consultas SQL, creacion de tablas y acceso a datos.

## CRUD principal

La entidad principal adaptada a la consigna es `cultivos`.

Operaciones implementadas:

- Crear: `/cultivos/nuevo`
- Leer: `/cultivos`
- Actualizar: `/cultivos/editar/<id>`
- Eliminar: `/cultivos/borrar/<id>`
- Reporte PDF: `/cultivos/reporte/pdf`

## Base de datos

El proyecto trabaja con MySQL/MariaDB.

Tablas principales relacionadas:

- `usuarios`
- `torres`
- `cultivos`
- `ciclos_cultivo`
- `lecturas_sensores`
- `configuracion_control`
- `actuadores_torre`
- `programaciones_riego`
- `alertas_sistema`
- `eventos_control`

El script SQL del proyecto esta en:

- `database/schema.sql`

Tambien puedes inicializar las tablas con:

```bash
flask mysql-init
```

## Variables de entorno

Configura estas variables en tu entorno local o despliegue:

```env
SECRET_KEY=cambia-esta-clave-secreta
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=ecogrow_mysql
MYSQL_UNIX_SOCKET=/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock
MYSQL_USE_SOCKET=true
MYSQL_AUTO_CREATE_DATABASE=true
MYSQL_SSL_DISABLED=true

ECOGROW_SENSOR_API_TOKEN=cambia-este-token-del-dispositivo
```

## Instalacion

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecucion

```bash
flask run
```

O tambien:

```bash
python3 app.py
```

## Rutas principales

### Publicas

- `/`
- `/about`
- `/contactos`
- `/demo`
- `/login`
- `/registro`

### Protegidas

- `/dashboard`
- `/torres`
- `/torres/registrar`
- `/torres/cultivo`
- `/cultivos`
- `/cultivos/nuevo`
- `/cultivos/reporte/pdf`
- `/sensores`
- `/mysql`
- `/mysql/usuarios`

## Reporte PDF

Se incluye generacion de PDF usando `fpdf2`.

Contenido del reporte:

- listado de cultivos registrados
- campos principales del cultivo
- fecha de generacion

## Pruebas

Ejecutar:

```bash
venv/bin/python -m unittest discover -s tests -v
```

## Entrega sugerida

Para la plataforma se entrega:

- enlace del repositorio GitHub
- proyecto Flask actualizado
- script SQL en `database/schema.sql`
- evidencia del CRUD de cultivos
- evidencia del reporte PDF

## Repositorio

`https://github.com/elJohn72/proyecto_ecogrow`
