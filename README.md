# EcoGrow

Aplicacion web academica desarrollada con Flask para gestionar un sistema hidropónico. El proyecto integra sitio publico, autenticacion de usuarios, panel protegido, gestion de torres y cultivos, CRUD de inventario, persistencia local y conexion con MySQL.

## Estado actual

Esta version cumple con la etapa de autenticacion solicitada:

- registro de usuarios en MySQL
- inicio y cierre de sesion
- proteccion de rutas con `Flask-Login`
- carga de usuario autenticado desde base de datos
- formularios HTML para registro y login
- persistencia relacional en MySQL y persistencia local en SQLite/archivos

## Tecnologias

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- MySQL Connector for Python
- MySQL / MariaDB
- Jinja2
- HTML + CSS
- PlatformIO + ESP32

## Estructura principal

```text
proyecto_ecogrow/
├── app.py
├── models.py
├── form.py
├── requirements.txt
├── .env.example
├── render.yaml
├── README.md
├── blueprints/
│   ├── auth.py
│   ├── cultivos.py
│   ├── inventario.py
│   ├── main.py
│   ├── mysql.py
│   ├── sensores.py
│   ├── shared.py
│   └── torres.py
├── Conexión/
│   ├── __init__.py
│   └── conexion.py
├── inventario/
│   ├── bd.py
│   ├── inventario.py
│   ├── productos.py
│   └── data/
├── database/
│   └── schema.sql
├── templates/
├── static/
├── tests/
│   └── test_app.py
└── platformio/
```

## Arquitectura

- `app.py`: crea la aplicacion Flask, inicializa `Flask-Login`, registra blueprints y comandos CLI.
- `models.py`: define la clase `User` compatible con `Flask-Login`.
- `blueprints/auth.py`: registro, login y logout.
- `blueprints/torres.py`: panel principal, torres y fases de cultivo.
- `blueprints/cultivos.py`: CRUD de cultivos.
- `blueprints/inventario.py`: CRUD local con SQLite y archivos.
- `blueprints/mysql.py`: vistas CRUD de usuarios y productos en MySQL.
- `blueprints/sensores.py`: monitoreo y endpoint de lecturas IoT.
- `Conexión/conexion.py`: acceso a MySQL, creacion de tablas y consultas.
- `form.py`: validacion basica de formularios.

## Autenticacion con Flask-Login

Se implemento autenticacion de usuarios usando `Flask-Login`.

### Funcionalidades

- Registro de usuario en `/registro`
- Inicio de sesion en `/login`
- Cierre de sesion en `/logout`
- Rutas protegidas con `@login_required`
- Redireccion automatica a login si el usuario no esta autenticado
- Carga del usuario desde MySQL con `user_loader`

### Tabla de usuarios

La autenticacion usa la tabla `usuarios` en MySQL:

```sql
CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    mail VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
```

Nota: en esta version las contrasenas se almacenan con hash por seguridad, aunque la consigna solo exigia almacenamiento para autenticacion. Esto mejora la implementacion y no rompe el requisito funcional.

## Variables de entorno

Copia `.env.example` como `.env` o configura estas variables en tu entorno:

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
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Base de datos

Puedes crear la estructura de MySQL de dos formas:

### Opcion 1: script SQL

Ejecuta `database/schema.sql` en tu servidor MySQL.

### Opcion 2: comando Flask

```bash
flask mysql-init
```

## Ejecucion

```bash
flask run
```

O tambien:

```bash
python app.py
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
- `/sensores`
- `/inventario`
- `/productos`
- `/mysql`

## Pruebas

Se agregaron pruebas basicas para:

- carga de rutas publicas
- proteccion de rutas privadas
- presencia de token CSRF
- rechazo de formularios sin CSRF
- login con credenciales validas simuladas
- validacion del endpoint IoT

Ejecutar:

```bash
python -m unittest discover -s tests -v
```

## Documentacion del equipo

Se agrego la carpeta `documentacion_equipo/` para centralizar material no relacionado con codigo sin afectar la arquitectura del proyecto.

- `documentacion_equipo/esquematicos/`: esquematicos, diagramas y conexiones.
- `documentacion_equipo/pdfs_actualizaciones/`: avances del proyecto en PDF.
- `documentacion_equipo/entregables/`: documentos formales para compartir.
- `documentacion_equipo/recursos_multimedia/`: imagenes, capturas y evidencias.
- `documentacion_equipo/notas_equipo/`: apuntes internos.
- `documentacion_equipo/presentaciones/`: exposiciones y diapositivas.

## Entrega sugerida

Para la plataforma se entrega:

- enlace del repositorio GitHub
- proyecto Flask actualizado
- script SQL en `database/schema.sql`
- evidencia de autenticacion con `Flask-Login`

## Repositorio

Repositorio GitHub:

`https://github.com/elJohn72/proyecto_ecogrow`
