import os
from pathlib import Path

import mysql.connector
from mysql.connector import Error

XAMPP_SOCKET_PATH = "/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock"


def _get_bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_render_environment() -> bool:
    return bool(os.getenv("RENDER"))


def _default_mysql_socket() -> str:
    if _is_render_environment():
        return ""
    return XAMPP_SOCKET_PATH if Path(XAMPP_SOCKET_PATH).exists() else ""


def _default_auto_create_database() -> bool:
    return not _is_render_environment()


# Variables de entorno recomendadas:
# MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD,
# MYSQL_DATABASE, MYSQL_UNIX_SOCKET, MYSQL_USE_SOCKET,
# MYSQL_AUTO_CREATE_DATABASE y MYSQL_SSL_DISABLED.
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "ecogrow_mysql"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "unix_socket": os.getenv("MYSQL_UNIX_SOCKET", _default_mysql_socket()),
    "use_socket": _get_bool_env("MYSQL_USE_SOCKET", bool(_default_mysql_socket())),
    "auto_create_database": _get_bool_env(
        "MYSQL_AUTO_CREATE_DATABASE",
        _default_auto_create_database(),
    ),
    "ssl_disabled": _get_bool_env("MYSQL_SSL_DISABLED", True),
    "is_render": _is_render_environment(),
}


def get_mysql_config_help() -> list[str]:
    return [
        "MYSQL_HOST: servidor MySQL o MariaDB.",
        "MYSQL_PORT: puerto TCP del servidor.",
        "MYSQL_USER: usuario con permisos sobre la base de datos.",
        "MYSQL_PASSWORD: contrasena del usuario MySQL.",
        "MYSQL_DATABASE: nombre de la base de datos del proyecto.",
        "MYSQL_UNIX_SOCKET: ruta del socket local, util en XAMPP para macOS.",
        "MYSQL_USE_SOCKET: activa el uso del socket local en vez de TCP.",
        "MYSQL_AUTO_CREATE_DATABASE: crea la base automaticamente si no existe.",
        "MYSQL_SSL_DISABLED: desactiva SSL si tu servidor local no lo soporta.",
    ]


def _connect(include_database: bool = True):
    config = {
        "host": MYSQL_CONFIG["host"],
        "user": MYSQL_CONFIG["user"],
        "password": MYSQL_CONFIG["password"],
        "port": MYSQL_CONFIG["port"],
        "ssl_disabled": MYSQL_CONFIG["ssl_disabled"],
    }
    if MYSQL_CONFIG["use_socket"] and MYSQL_CONFIG["unix_socket"]:
        config["unix_socket"] = MYSQL_CONFIG["unix_socket"]
    if include_database:
        config["database"] = MYSQL_CONFIG["database"]
    return mysql.connector.connect(**config)


def create_mysql_tables() -> None:
    if MYSQL_CONFIG["auto_create_database"]:
        server_connection = _connect(include_database=False)
        try:
            with server_connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
                )
            server_connection.commit()
        finally:
            server_connection.close()

    database_connection = _connect(include_database=True)
    try:
        with database_connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    mail VARCHAR(120) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS productos (
                    id_producto INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(120) NOT NULL UNIQUE,
                    cantidad INT NOT NULL,
                    precio DECIMAL(10,2) NOT NULL,
                    descripcion VARCHAR(255) NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lecturas_sensores (
                    id_lectura INT AUTO_INCREMENT PRIMARY KEY,
                    dispositivo VARCHAR(100) NOT NULL,
                    temperatura_aire DECIMAL(5,2),
                    humedad_aire DECIMAL(5,2),
                    temperatura_agua DECIMAL(5,2),
                    ph DECIMAL(4,2),
                    ec DECIMAL(5,2),
                    nivel_agua DECIMAL(5,2),
                    luminosidad DECIMAL(8,2),
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        database_connection.commit()
    finally:
        database_connection.close()


def get_mysql_status() -> dict:
    status = {
        "available": False,
        "message": "",
        "config": MYSQL_CONFIG.copy(),
        "help": get_mysql_config_help(),
    }
    try:
        create_mysql_tables()
        status["available"] = True
        status["message"] = "Conexion MySQL disponible. Base de datos y tablas verificadas."
    except Error as exc:
        status["message"] = f"No se pudo conectar a MySQL: {exc}"
    return status


def _execute(query: str, params=None, *, fetchone: bool = False, fetchall: bool = False):
    connection = _connect(include_database=True)
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params or ())
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            connection.commit()
            return cursor.lastrowid
    finally:
        connection.close()


def fetch_mysql_usuarios() -> list[dict]:
    create_mysql_tables()
    return _execute("SELECT * FROM usuarios ORDER BY id_usuario ASC", fetchall=True)


def fetch_mysql_usuario(usuario_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        "SELECT * FROM usuarios WHERE id_usuario = %s",
        (usuario_id,),
        fetchone=True,
    )


def insert_mysql_usuario(nombre: str, mail: str, password: str) -> int:
    create_mysql_tables()
    return _execute(
        "INSERT INTO usuarios (nombre, mail, password) VALUES (%s, %s, %s)",
        (nombre, mail, password),
    )


def update_mysql_usuario(usuario_id: int, nombre: str, mail: str, password: str) -> None:
    create_mysql_tables()
    _execute(
        """
        UPDATE usuarios
        SET nombre = %s, mail = %s, password = %s
        WHERE id_usuario = %s
        """,
        (nombre, mail, password, usuario_id),
    )


def delete_mysql_usuario(usuario_id: int) -> None:
    create_mysql_tables()
    _execute("DELETE FROM usuarios WHERE id_usuario = %s", (usuario_id,))


def fetch_mysql_productos() -> list[dict]:
    create_mysql_tables()
    return _execute("SELECT * FROM productos ORDER BY id_producto ASC", fetchall=True)


def fetch_mysql_producto(producto_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        "SELECT * FROM productos WHERE id_producto = %s",
        (producto_id,),
        fetchone=True,
    )


def insert_mysql_producto(nombre: str, cantidad: int, precio: float, descripcion: str) -> int:
    create_mysql_tables()
    return _execute(
        """
        INSERT INTO productos (nombre, cantidad, precio, descripcion)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre, cantidad, precio, descripcion),
    )


def update_mysql_producto(
    producto_id: int,
    nombre: str,
    cantidad: int,
    precio: float,
    descripcion: str,
) -> None:
    create_mysql_tables()
    _execute(
        """
        UPDATE productos
        SET nombre = %s, cantidad = %s, precio = %s, descripcion = %s
        WHERE id_producto = %s
        """,
        (nombre, cantidad, precio, descripcion, producto_id),
    )


def delete_mysql_producto(producto_id: int) -> None:
    create_mysql_tables()
    _execute("DELETE FROM productos WHERE id_producto = %s", (producto_id,))


def insert_sensor_reading(
    dispositivo: str,
    temperatura_aire: float | None,
    humedad_aire: float | None,
    temperatura_agua: float | None,
    ph: float | None,
    ec: float | None,
    nivel_agua: float | None,
    luminosidad: float | None,
) -> int:
    create_mysql_tables()
    return _execute(
        """
        INSERT INTO lecturas_sensores (
            dispositivo,
            temperatura_aire,
            humedad_aire,
            temperatura_agua,
            ph,
            ec,
            nivel_agua,
            luminosidad
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            dispositivo,
            temperatura_aire,
            humedad_aire,
            temperatura_agua,
            ph,
            ec,
            nivel_agua,
            luminosidad,
        ),
    )


def fetch_sensor_readings(limit: int = 20) -> list[dict]:
    create_mysql_tables()
    return _execute(
        """
        SELECT *
        FROM lecturas_sensores
        ORDER BY fecha_registro DESC, id_lectura DESC
        LIMIT %s
        """,
        (limit,),
        fetchall=True,
    )


def fetch_latest_sensor_reading() -> dict | None:
    create_mysql_tables()
    return _execute(
        """
        SELECT *
        FROM lecturas_sensores
        ORDER BY fecha_registro DESC, id_lectura DESC
        LIMIT 1
        """,
        fetchone=True,
    )
