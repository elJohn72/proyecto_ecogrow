import os
from pathlib import Path

import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

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
    try:
        return mysql.connector.connect(**config)
    except Error:
        if "unix_socket" not in config:
            raise

        fallback_config = config.copy()
        fallback_config.pop("unix_socket", None)
        return mysql.connector.connect(**fallback_config)


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
                CREATE TABLE IF NOT EXISTS cultivos (
                    id_cultivo INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(120) NOT NULL,
                    variedad VARCHAR(120) NOT NULL,
                    ubicacion VARCHAR(120) NOT NULL,
                    estado VARCHAR(80) NOT NULL,
                    descripcion VARCHAR(255) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS torres (
                    id_torre INT AUTO_INCREMENT PRIMARY KEY,
                    codigo_unico VARCHAR(80) NOT NULL UNIQUE,
                    nombre VARCHAR(120) NOT NULL,
                    ubicacion VARCHAR(120) NOT NULL,
                    usuario_id INT NOT NULL,
                    estado VARCHAR(40) NOT NULL DEFAULT 'registrada',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_torres_usuario
                        FOREIGN KEY (usuario_id) REFERENCES usuarios(id_usuario)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ciclos_cultivo (
                    id_ciclo INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL,
                    cultivo_id INT NOT NULL,
                    fase VARCHAR(80) NOT NULL,
                    notas VARCHAR(255) NOT NULL DEFAULT '',
                    estado VARCHAR(40) NOT NULL DEFAULT 'activo',
                    iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finalizado_en TIMESTAMP NULL DEFAULT NULL,
                    CONSTRAINT fk_ciclos_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_ciclos_cultivo
                        FOREIGN KEY (cultivo_id) REFERENCES cultivos(id_cultivo)
                        ON DELETE RESTRICT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lecturas_sensores (
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
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_lecturas_ciclo
                        FOREIGN KEY (ciclo_id) REFERENCES ciclos_cultivo(id_ciclo)
                        ON DELETE RESTRICT
                )
                """
            )
            _ensure_lecturas_schema(cursor)
        database_connection.commit()
    finally:
        database_connection.close()


def _ensure_lecturas_schema(cursor) -> None:
    cursor.execute("SHOW COLUMNS FROM lecturas_sensores LIKE 'ciclo_id'")
    ciclo_column = cursor.fetchone()
    if not ciclo_column:
        cursor.execute("ALTER TABLE lecturas_sensores ADD COLUMN ciclo_id INT NULL AFTER id_lectura")

    cursor.execute("SHOW INDEX FROM lecturas_sensores WHERE Key_name = 'fk_lecturas_ciclo'")
    ciclo_fk_exists = cursor.fetchone()
    if not ciclo_fk_exists:
        try:
            cursor.execute(
                """
                ALTER TABLE lecturas_sensores
                ADD CONSTRAINT fk_lecturas_ciclo
                FOREIGN KEY (ciclo_id) REFERENCES ciclos_cultivo(id_ciclo)
                ON DELETE RESTRICT
                """
            )
        except Error:
            pass


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


def fetch_mysql_user_by_credentials(mail: str, password: str) -> dict | None:
    return verify_mysql_user_credentials(mail, password)


def verify_mysql_user_credentials(mail: str, password: str) -> dict | None:
    create_mysql_tables()
    usuario = _execute(
        "SELECT * FROM usuarios WHERE mail = %s LIMIT 1",
        (mail,),
        fetchone=True,
    )
    if not usuario:
        return None

    stored_password = usuario["password"]
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return usuario if check_password_hash(stored_password, password) else None

    if stored_password == password:
        _execute(
            "UPDATE usuarios SET password = %s WHERE id_usuario = %s",
            (generate_password_hash(password), usuario["id_usuario"]),
        )
        usuario["password"] = ""
        return usuario

    return None


def fetch_mysql_user_by_mail(mail: str) -> dict | None:
    create_mysql_tables()
    return _execute(
        "SELECT * FROM usuarios WHERE mail = %s LIMIT 1",
        (mail,),
        fetchone=True,
    )


def insert_mysql_usuario(nombre: str, mail: str, password: str) -> int:
    create_mysql_tables()
    return _execute(
        "INSERT INTO usuarios (nombre, mail, password) VALUES (%s, %s, %s)",
        (nombre, mail, generate_password_hash(password)),
    )


def update_mysql_usuario(
    usuario_id: int,
    nombre: str,
    mail: str,
    password: str | None = None,
) -> None:
    create_mysql_tables()
    if password:
        _execute(
            """
            UPDATE usuarios
            SET nombre = %s, mail = %s, password = %s
            WHERE id_usuario = %s
            """,
            (nombre, mail, generate_password_hash(password), usuario_id),
        )
        return

    _execute(
        """
        UPDATE usuarios
        SET nombre = %s, mail = %s
        WHERE id_usuario = %s
        """,
        (nombre, mail, usuario_id),
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


def fetch_cultivos() -> list[dict]:
    create_mysql_tables()
    return _execute("SELECT * FROM cultivos ORDER BY creado_en DESC, id_cultivo DESC", fetchall=True)


def fetch_cultivo(cultivo_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        "SELECT * FROM cultivos WHERE id_cultivo = %s",
        (cultivo_id,),
        fetchone=True,
    )


def insert_cultivo(nombre: str, variedad: str, ubicacion: str, estado: str, descripcion: str) -> int:
    create_mysql_tables()
    return _execute(
        """
        INSERT INTO cultivos (nombre, variedad, ubicacion, estado, descripcion)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (nombre, variedad, ubicacion, estado, descripcion),
    )


def update_cultivo(
    cultivo_id: int,
    nombre: str,
    variedad: str,
    ubicacion: str,
    estado: str,
    descripcion: str,
) -> None:
    create_mysql_tables()
    _execute(
        """
        UPDATE cultivos
        SET nombre = %s, variedad = %s, ubicacion = %s, estado = %s, descripcion = %s
        WHERE id_cultivo = %s
        """,
        (nombre, variedad, ubicacion, estado, descripcion, cultivo_id),
    )


def delete_cultivo(cultivo_id: int) -> None:
    create_mysql_tables()
    _execute("DELETE FROM cultivos WHERE id_cultivo = %s", (cultivo_id,))


def fetch_torres_by_user(usuario_id: int) -> list[dict]:
    create_mysql_tables()
    return _execute(
        """
        SELECT torres.*, cultivos.nombre AS cultivo_activo_nombre, ciclos_cultivo.fase AS fase_activa
        FROM torres
        LEFT JOIN ciclos_cultivo
            ON ciclos_cultivo.torre_id = torres.id_torre
            AND ciclos_cultivo.estado = 'activo'
        LEFT JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE torres.usuario_id = %s
        ORDER BY torres.creado_en DESC, torres.id_torre DESC
        """,
        (usuario_id,),
        fetchall=True,
    )


def fetch_torre(torre_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        """
        SELECT torres.*, cultivos.nombre AS cultivo_activo_nombre, ciclos_cultivo.fase AS fase_activa
        FROM torres
        LEFT JOIN ciclos_cultivo
            ON ciclos_cultivo.torre_id = torres.id_torre
            AND ciclos_cultivo.estado = 'activo'
        LEFT JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE torres.id_torre = %s
        LIMIT 1
        """,
        (torre_id,),
        fetchone=True,
    )


def fetch_torre_by_codigo(codigo_unico: str) -> dict | None:
    create_mysql_tables()
    return _execute(
        "SELECT * FROM torres WHERE codigo_unico = %s LIMIT 1",
        (codigo_unico.upper(),),
        fetchone=True,
    )


def insert_torre(codigo_unico: str, nombre: str, ubicacion: str, usuario_id: int) -> int:
    create_mysql_tables()
    return _execute(
        """
        INSERT INTO torres (codigo_unico, nombre, ubicacion, usuario_id)
        VALUES (%s, %s, %s, %s)
        """,
        (codigo_unico.upper(), nombre, ubicacion, usuario_id),
    )


def register_torre(codigo_unico: str, nombre: str, ubicacion: str, usuario_id: int) -> int:
    create_mysql_tables()
    codigo_normalizado = codigo_unico.upper()
    existente = fetch_torre_by_codigo(codigo_normalizado)
    if existente:
        if existente["usuario_id"] != usuario_id:
            raise ValueError("Ese codigo de torre ya pertenece a otro usuario.")
        _execute(
            """
            UPDATE torres
            SET nombre = %s, ubicacion = %s
            WHERE id_torre = %s
            """,
            (nombre, ubicacion, existente["id_torre"]),
        )
        return existente["id_torre"]
    return insert_torre(codigo_normalizado, nombre, ubicacion, usuario_id)


def fetch_active_cycle_by_torre(torre_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        """
        SELECT ciclos_cultivo.*, cultivos.nombre AS cultivo_nombre
        FROM ciclos_cultivo
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE ciclos_cultivo.torre_id = %s
          AND ciclos_cultivo.estado = 'activo'
        ORDER BY ciclos_cultivo.iniciado_en DESC, ciclos_cultivo.id_ciclo DESC
        LIMIT 1
        """,
        (torre_id,),
        fetchone=True,
    )


def fetch_cycles_by_torre(torre_id: int, limit: int = 10) -> list[dict]:
    create_mysql_tables()
    return _execute(
        """
        SELECT ciclos_cultivo.*, cultivos.nombre AS cultivo_nombre
        FROM ciclos_cultivo
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE ciclos_cultivo.torre_id = %s
        ORDER BY ciclos_cultivo.iniciado_en DESC, ciclos_cultivo.id_ciclo DESC
        LIMIT %s
        """,
        (torre_id, limit),
        fetchall=True,
    )


def start_cultivo_cycle(torre_id: int, cultivo_id: int, fase: str, notas: str) -> int:
    create_mysql_tables()
    _execute(
        """
        UPDATE ciclos_cultivo
        SET estado = 'finalizado', finalizado_en = CURRENT_TIMESTAMP
        WHERE torre_id = %s AND estado = 'activo'
        """,
        (torre_id,),
    )
    return _execute(
        """
        INSERT INTO ciclos_cultivo (torre_id, cultivo_id, fase, notas, estado)
        VALUES (%s, %s, %s, %s, 'activo')
        """,
        (torre_id, cultivo_id, fase, notas),
    )


def close_active_cycle(torre_id: int) -> None:
    create_mysql_tables()
    _execute(
        """
        UPDATE ciclos_cultivo
        SET estado = 'finalizado', finalizado_en = CURRENT_TIMESTAMP
        WHERE torre_id = %s AND estado = 'activo'
        """,
        (torre_id,),
    )


def insert_sensor_reading(
    torre_codigo: str,
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
    torre = fetch_torre_by_codigo(torre_codigo)
    if not torre:
        raise ValueError("La torre indicada no existe.")

    ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
    if not ciclo_activo:
        raise ValueError("La torre indicada no tiene un cultivo activo configurado.")

    ciclo_id = ciclo_activo["id_ciclo"]

    return _execute(
        """
        INSERT INTO lecturas_sensores (
            ciclo_id,
            dispositivo,
            temperatura_aire,
            humedad_aire,
            temperatura_agua,
            ph,
            ec,
            nivel_agua,
            luminosidad
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            ciclo_id,
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
        SELECT
            lecturas_sensores.*,
            cultivos.nombre AS cultivo_nombre,
            torres.codigo_unico AS torre_codigo,
            torres.nombre AS torre_nombre
        FROM lecturas_sensores
        INNER JOIN ciclos_cultivo ON ciclos_cultivo.id_ciclo = lecturas_sensores.ciclo_id
        INNER JOIN torres ON torres.id_torre = ciclos_cultivo.torre_id
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
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
        SELECT
            lecturas_sensores.*,
            cultivos.nombre AS cultivo_nombre,
            torres.codigo_unico AS torre_codigo,
            torres.nombre AS torre_nombre
        FROM lecturas_sensores
        INNER JOIN ciclos_cultivo ON ciclos_cultivo.id_ciclo = lecturas_sensores.ciclo_id
        INNER JOIN torres ON torres.id_torre = ciclos_cultivo.torre_id
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        ORDER BY fecha_registro DESC, id_lectura DESC
        LIMIT 1
        """,
        fetchone=True,
    )


def fetch_sensor_readings_by_torre(torre_id: int, limit: int = 20) -> list[dict]:
    create_mysql_tables()
    return _execute(
        """
        SELECT
            lecturas_sensores.*,
            cultivos.nombre AS cultivo_nombre,
            torres.codigo_unico AS torre_codigo,
            torres.nombre AS torre_nombre
        FROM lecturas_sensores
        INNER JOIN ciclos_cultivo ON ciclos_cultivo.id_ciclo = lecturas_sensores.ciclo_id
        INNER JOIN torres ON torres.id_torre = ciclos_cultivo.torre_id
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE ciclos_cultivo.torre_id = %s
        ORDER BY fecha_registro DESC, id_lectura DESC
        LIMIT %s
        """,
        (torre_id, limit),
        fetchall=True,
    )


def fetch_latest_sensor_reading_by_torre(torre_id: int) -> dict | None:
    create_mysql_tables()
    return _execute(
        """
        SELECT
            lecturas_sensores.*,
            cultivos.nombre AS cultivo_nombre,
            torres.codigo_unico AS torre_codigo,
            torres.nombre AS torre_nombre
        FROM lecturas_sensores
        INNER JOIN ciclos_cultivo ON ciclos_cultivo.id_ciclo = lecturas_sensores.ciclo_id
        INNER JOIN torres ON torres.id_torre = ciclos_cultivo.torre_id
        INNER JOIN cultivos ON cultivos.id_cultivo = ciclos_cultivo.cultivo_id
        WHERE ciclos_cultivo.torre_id = %s
        ORDER BY fecha_registro DESC, id_lectura DESC
        LIMIT 1
        """,
        (torre_id,),
        fetchone=True,
    )
