# EcoGrow

Aplicacion web desarrollada con Flask para la gestion de un sistema hidropónico academico. El proyecto ha evolucionado por semanas incorporando rutas, plantillas Jinja2, CRUD, persistencia en archivos, SQLite y conexion con MySQL/MariaDB.

## Objetivo del proyecto

EcoGrow permite demostrar en un mismo sistema:

- Desarrollo web con Flask.
- Uso de plantillas HTML con herencia.
- CRUD de productos.
- Persistencia en multiples formatos: TXT, JSON, CSV y SQLite.
- Integracion con base de datos relacional externa usando MySQL/MariaDB.
- Integracion de sensores IoT con ESP32 usando PlatformIO.

## Arquitectura del proyecto

La arquitectura actual es adecuada para una entrega academica porque separa responsabilidades por modulos:

- `app.py`: punto de entrada, configuracion Flask y definicion de rutas.
- `form.py`: validacion basica de formularios para productos y usuarios.
- `inventario/`: logica del inventario local con SQLite y sincronizacion a archivos.
- `Conexión/`: capa de conexion y consultas CRUD hacia MySQL/MariaDB.
- `platformio/`: firmware base para ESP32 y envio de lecturas.
- `templates/`: vistas HTML del sistema.
- `static/`: estilos CSS.

### Criterio arquitectonico

El proyecto usa dos capas de persistencia:

- Persistencia local:
  SQLite + archivos TXT, JSON y CSV.
- Persistencia externa:
  MySQL/MariaDB para tablas relacionales del sistema.

Esto cumple con las tareas pedidas en semanas distintas. Para una version de produccion futura, lo recomendable seria unificar el acceso a datos en una sola estrategia y retirar archivos o modulos heredados que ya no se usen.

## Estructura del proyecto

```text
proyecto_ecogrow/
├── app.py
├── form.py
├── requirements.txt
├── .gitignore
├── .env.example
├── __init__.py
├── inventario.db
├── render.yaml
├── README.md
├── Conexión/
│   ├── __init__.py
│   └── conexion.py
├── inventario/
│   ├── __init__.py
│   ├── bd.py
│   ├── inventario.py
│   ├── productos.py
│   └── data/
│       ├── datos.txt
│       ├── datos.json
│       └── datos.csv
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── about.html
    ├── contactos.html
    ├── cultivos.html
    ├── sensores.html
    ├── irrigation.html
    ├── dashboard.html
    ├── sustainability.html
    ├── productos.html
    ├── producto_form.html
    ├── datos.html
    ├── mysql_dashboard.html
    ├── mysql_usuarios.html
    ├── mysql_usuario_form.html
    ├── mysql_productos.html
    └── mysql_producto_form.html
```

## Tecnologias utilizadas

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLite
- MySQL Connector for Python
- MySQL o MariaDB
- HTML + Jinja2
- Tailwind CSS por CDN

## Modulos principales

### 1. Flask y rutas

El archivo `app.py` contiene:

- configuracion principal de Flask
- inicializacion de SQLite
- rutas informativas del sitio
- CRUD de inventario local
- vista de datos persistidos
- CRUD de usuarios y productos en MySQL

### 2. Inventario local

La carpeta `inventario/` maneja el almacenamiento local:

- `bd.py`: inicializa SQLAlchemy y asegura archivos de datos.
- `productos.py`: define el modelo `Producto` para SQLite.
- `inventario.py`: implementa operaciones CRUD y sincronizacion a TXT, JSON y CSV.

### 3. Conexion a MySQL

La carpeta `Conexión/` contiene:

- configuracion de acceso a MySQL/MariaDB
- creacion de la base de datos si no existe
- creacion de tablas `usuarios`, `productos`, `cultivos`, `torres`, `ciclos_cultivo` y `lecturas_sensores`
- operaciones CRUD basicas
- almacenamiento de lecturas de sensores

### 4. Integracion IoT con PlatformIO

La carpeta `platformio/esp32_hidroponico/` contiene un proyecto base para ESP32 que:

- se conecta por WiFi
- construye un JSON con lecturas del sistema
- envia datos a Flask mediante `HTTP POST`

### 5. Formularios

`form.py` centraliza la validacion de:

- productos
- usuarios
- login
- cultivos
- torres
- fases de cultivo por torre

## Persistencia de datos

### Persistencia en archivos

Los productos almacenados localmente se sincronizan automaticamente en:

- `inventario/data/datos.txt`
- `inventario/data/datos.json`
- `inventario/data/datos.csv`

### Persistencia en SQLite

El archivo `inventario.db` guarda el inventario local mediante `Flask-SQLAlchemy`.

### Persistencia en MySQL/MariaDB

El sistema tambien permite trabajar con una base relacional externa usando:

- tabla `usuarios`
- tabla `productos`
- tabla `cultivos`
- tabla `torres`
- tabla `ciclos_cultivo`
- tabla `lecturas_sensores`

## Tablas principales

### Tabla `usuarios`

```sql
CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    mail VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
```

### Tabla `productos`

```sql
CREATE TABLE productos (
    id_producto INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    cantidad INT NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    descripcion VARCHAR(255) NOT NULL
);
```

### Tabla `torres`

```sql
CREATE TABLE torres (
    id_torre INT AUTO_INCREMENT PRIMARY KEY,
    codigo_unico VARCHAR(80) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    ubicacion VARCHAR(120) NOT NULL,
    usuario_id INT NOT NULL,
    estado VARCHAR(40) NOT NULL DEFAULT 'registrada'
);
```

### Tabla `ciclos_cultivo`

```sql
CREATE TABLE ciclos_cultivo (
    id_ciclo INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL,
    cultivo_id INT NOT NULL,
    fase VARCHAR(80) NOT NULL,
    notas VARCHAR(255) NOT NULL DEFAULT '',
    estado VARCHAR(40) NOT NULL DEFAULT 'activo',
    iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalizado_en TIMESTAMP NULL DEFAULT NULL
);
```

### Tabla `lecturas_sensores`

```sql
CREATE TABLE lecturas_sensores (
    id_lectura INT AUTO_INCREMENT PRIMARY KEY,
    ciclo_id INT NOT NULL,
    dispositivo VARCHAR(100) NOT NULL,
    temperatura_aire DECIMAL(5,2),
    humedad_aire DECIMAL(5,2),
    temperatura_agua DECIMAL(5,2),
    ph DECIMAL(4,2),
    ec DECIMAL(5,2),
    nivel_agua DECIMAL(5,2),
    luminosidad DECIMAL(8,2),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla `cultivos`

```sql
CREATE TABLE cultivos (
    id_cultivo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    variedad VARCHAR(120) NOT NULL,
    ubicacion VARCHAR(120) NOT NULL,
    estado VARCHAR(80) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Rutas principales

### Sitio general

- `/`
- `/about`
- `/contactos`
- `/login`
- `/logout`
- `/demo`
- `/planta/<nombre>`

### Panel autenticado

- `/dashboard`
- `/torres`
- `/torres/registrar`
- `/torres/seleccionar/<id>`
- `/torres/cultivo`
- `/torres/cultivo/finalizar`
- `/cultivos`
- `/cultivos/nuevo`
- `/cultivos/editar/<id>`
- `/cultivos/borrar/<id>`
- `/sensores`
- `/api/sensores/lectura`
- `/irrigation`
- `/sustainability`

### Inventario local

- `/inventario`
- `/inventario/crear`
- `/inventario/editar/<id>`
- `/inventario/borrar/<id>`
- `/datos`

### MySQL

- `/mysql`
- `/mysql/inicializar`
- `/mysql/usuarios`
- `/mysql/usuarios/crear`
- `/mysql/usuarios/editar/<id>`
- `/mysql/usuarios/borrar/<id>`
- `/mysql/productos`
- `/mysql/productos/crear`
- `/mysql/productos/editar/<id>`
- `/mysql/productos/borrar/<id>`

## Configuracion local

### 1. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar MySQL

Usa el archivo `.env.example` como referencia:

```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=ecogrow_mysql
MYSQL_UNIX_SOCKET=/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock
MYSQL_USE_SOCKET=true
MYSQL_AUTO_CREATE_DATABASE=true
MYSQL_SSL_DISABLED=true
```

En macOS con XAMPP, el acceso por `unix_socket` puede ser necesario para conectarse correctamente a MariaDB.

### Configuracion recomendada para Render

En Render no debes usar el socket de XAMPP. Debes definir variables de entorno reales del servicio MySQL o MariaDB:

```bash
MYSQL_HOST=tu-host-render-o-externo
MYSQL_PORT=3306
MYSQL_USER=tu_usuario
MYSQL_PASSWORD=tu_password
MYSQL_DATABASE=tu_base
MYSQL_USE_SOCKET=false
MYSQL_AUTO_CREATE_DATABASE=false
MYSQL_SSL_DISABLED=true
```

La aplicacion ya detecta Render y evita usar el socket local por defecto.

### 4. Ejecutar la aplicacion

```bash
venv/bin/python app.py
```

## Comandos utiles

### Sincronizar archivos TXT, JSON y CSV desde SQLite

```bash
venv/bin/flask sincronizar-datos
```

### Inicializar la base de datos MySQL

```bash
venv/bin/flask mysql-init
```

## Integracion con sensores

La aplicacion ya puede recibir lecturas desde un ESP32 con PlatformIO a traves de:

```http
POST /api/sensores/lectura
Content-Type: application/json
```

Ejemplo de payload:

```json
{
  "torre_codigo": "ECO-TORRE-001",
  "dispositivo": "esp32_torre_1",
  "temperatura_aire": 24.5,
  "humedad_aire": 67.0,
  "temperatura_agua": 22.8,
  "ph": 6.1,
  "ec": 1.75,
  "nivel_agua": 73.0,
  "luminosidad": 540.0
}
```

El dashboard de sensores muestra:

- torre asociada a la lectura
- cultivo activo de la fase actual
- ultima lectura recibida
- historial reciente
- endpoint a consumir desde el ESP32

## Modelo funcional del sistema hidropónico

EcoGrow ahora separa tres conceptos:

- `torre`: estructura fisica que el cliente registra una sola vez con un codigo unico.
- `cultivo`: catalogo de tipos de cultivo disponibles para usar en el sistema.
- `ciclo_cultivo`: fase activa de una torre en un momento dado. Cuando termina la cosecha, se puede cerrar el ciclo y abrir otro con el mismo cultivo o con uno distinto.

Las `lecturas_sensores` dependen del `ciclo_cultivo`, no guardan `cultivo_id` ni `torre_id` como columnas de trabajo. Esa decision evita redundancia y acerca el modelo a una tercera forma normal real: desde `ciclo_id` se obtiene tanto la torre como el cultivo asociado.

## Despliegue en Render

El proyecto incluye `render.yaml` para despliegue.

Consideraciones:

- SQLite y archivos locales no son la mejor opcion para persistencia en produccion si el sistema de archivos es efimero.
- Para MySQL en Render se deben usar variables de entorno reales del servicio o de una base externa.
- No se debe usar la configuracion local de XAMPP en Render.
- `render.yaml` ya incluye las claves MySQL esperadas para configurarlas desde Render.

## Estado actual de la arquitectura

La arquitectura esta bien para la etapa actual del proyecto porque:

- separa la capa web de la capa de datos
- diferencia la persistencia local de la relacional externa
- organiza las vistas por funcionalidad
- mantiene un punto de entrada claro

## Mejoras futuras recomendadas

- agregar un archivo `.env` real con carga automatica usando `python-dotenv`
- unificar nombres de plantillas antiguas que ya no se usan
- separar las rutas en blueprints
- hash de contrasenas para usuarios en MySQL
- agregar pruebas automatizadas

## Autor y contexto

Proyecto academico desarrollado para la materia de aplicaciones web / bases de datos, integrando Flask, persistencia de datos y bases relacionales externas.
