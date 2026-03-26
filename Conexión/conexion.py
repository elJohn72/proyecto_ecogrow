import os
from pathlib import Path

import mysql.connector
from mysql.connector import Error, ProgrammingError
from werkzeug.security import check_password_hash, generate_password_hash

XAMPP_SOCKET_PATH = "/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock"
COMMON_SOCKET_PATHS = (
    XAMPP_SOCKET_PATH,
    "/tmp/mysql.sock",
    "/opt/homebrew/var/run/mysqld/mysqld.sock",
)


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
    for socket_path in COMMON_SOCKET_PATHS:
        if Path(socket_path).exists():
            return socket_path
    return ""


def _default_auto_create_database() -> bool:
    return not _is_render_environment()


def _default_local_mysql_user() -> str:
    return os.getenv("USER", "root")


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

CONTROL_DEFAULTS = {
    "module_size_mm": 80,
    "deposito_litros": 5.0,
    "bomba_modelo": "Aqua One Maxi 103",
    "head_height_m": 1.4,
    "ph_min": 6.5,
    "ph_max": 8.5,
    "ec_min": 1.4,
    "ec_max": 2.4,
    "temperatura_agua_min": 18.0,
    "temperatura_agua_max": 24.0,
    "nivel_minimo": 20.0,
    "nivel_objetivo": 85.0,
    "irrigation_on_minutes": 15,
    "irrigation_off_minutes": 60,
    "control_mode": "consenso",
    "pid_kp": 0.5,
    "pid_ki": 1.0,
    "pid_kd": 1.0,
    "consenso_pid_weight": 0.8,
    "consenso_fuzzy_weight": 0.2,
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
    except ProgrammingError as exc:
        if os.getenv("MYSQL_USER") or config.get("user") != "root":
            raise

        fallback_user = _default_local_mysql_user()
        if fallback_user == "root":
            raise

        fallback_config = config.copy()
        fallback_config["user"] = fallback_user
        return mysql.connector.connect(**fallback_config)
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS configuracion_control (
                    id_configuracion INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL UNIQUE,
                    module_size_mm INT NOT NULL DEFAULT 80,
                    deposito_litros DECIMAL(6,2) NOT NULL DEFAULT 5.00,
                    bomba_modelo VARCHAR(120) NOT NULL DEFAULT 'Aqua One Maxi 103',
                    head_height_m DECIMAL(5,2) NOT NULL DEFAULT 1.40,
                    ph_min DECIMAL(4,2) NOT NULL DEFAULT 6.50,
                    ph_max DECIMAL(4,2) NOT NULL DEFAULT 8.50,
                    ec_min DECIMAL(5,2) NOT NULL DEFAULT 1.40,
                    ec_max DECIMAL(5,2) NOT NULL DEFAULT 2.40,
                    temperatura_agua_min DECIMAL(5,2) NOT NULL DEFAULT 18.00,
                    temperatura_agua_max DECIMAL(5,2) NOT NULL DEFAULT 24.00,
                    nivel_minimo DECIMAL(5,2) NOT NULL DEFAULT 20.00,
                    nivel_objetivo DECIMAL(5,2) NOT NULL DEFAULT 85.00,
                    irrigation_on_minutes INT NOT NULL DEFAULT 15,
                    irrigation_off_minutes INT NOT NULL DEFAULT 60,
                    control_mode VARCHAR(40) NOT NULL DEFAULT 'consenso',
                    pid_kp DECIMAL(6,3) NOT NULL DEFAULT 0.500,
                    pid_ki DECIMAL(6,3) NOT NULL DEFAULT 1.000,
                    pid_kd DECIMAL(6,3) NOT NULL DEFAULT 1.000,
                    consenso_pid_weight DECIMAL(5,2) NOT NULL DEFAULT 0.80,
                    consenso_fuzzy_weight DECIMAL(5,2) NOT NULL DEFAULT 0.20,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_configuracion_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS actuadores_torre (
                    id_actuador INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL,
                    tipo VARCHAR(60) NOT NULL,
                    nombre VARCHAR(120) NOT NULL,
                    estado VARCHAR(40) NOT NULL DEFAULT 'listo',
                    modo VARCHAR(40) NOT NULL DEFAULT 'automatico',
                    ultimo_comando VARCHAR(120) NOT NULL DEFAULT 'sin accion',
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_actuador_torre_tipo (torre_id, tipo),
                    CONSTRAINT fk_actuador_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS programaciones_riego (
                    id_programacion INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL UNIQUE,
                    habilitado BOOLEAN NOT NULL DEFAULT TRUE,
                    minutos_encendido INT NOT NULL DEFAULT 15,
                    minutos_apagado INT NOT NULL DEFAULT 60,
                    estrategia VARCHAR(80) NOT NULL DEFAULT 'oxigenacion_radicular',
                    siguiente_ciclo VARCHAR(80) NOT NULL DEFAULT 'inmediato',
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_programacion_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alertas_sistema (
                    id_alerta INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL,
                    tipo VARCHAR(60) NOT NULL,
                    severidad VARCHAR(30) NOT NULL,
                    mensaje VARCHAR(255) NOT NULL,
                    valor_actual DECIMAL(8,2) NULL,
                    umbral_referencia VARCHAR(120) NOT NULL,
                    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
                    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cerrada_en TIMESTAMP NULL DEFAULT NULL,
                    CONSTRAINT fk_alerta_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_control (
                    id_evento INT AUTO_INCREMENT PRIMARY KEY,
                    torre_id INT NOT NULL,
                    lectura_id INT NULL,
                    algoritmo VARCHAR(40) NOT NULL,
                    variable_control VARCHAR(40) NOT NULL,
                    error_valor DECIMAL(8,3) NOT NULL,
                    salida_pid DECIMAL(8,3) NOT NULL,
                    salida_fuzzy DECIMAL(8,3) NOT NULL,
                    salida_consenso DECIMAL(8,3) NOT NULL,
                    accion_recomendada VARCHAR(120) NOT NULL,
                    motivo VARCHAR(255) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_evento_torre
                        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_evento_lectura
                        FOREIGN KEY (lectura_id) REFERENCES lecturas_sensores(id_lectura)
                        ON DELETE SET NULL
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


def _create_control_defaults_for_torre(torre_id: int) -> None:
    create_mysql_tables()
    connection = _connect(include_database=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO configuracion_control (
                    torre_id,
                    module_size_mm,
                    deposito_litros,
                    bomba_modelo,
                    head_height_m,
                    ph_min,
                    ph_max,
                    ec_min,
                    ec_max,
                    temperatura_agua_min,
                    temperatura_agua_max,
                    nivel_minimo,
                    nivel_objetivo,
                    irrigation_on_minutes,
                    irrigation_off_minutes,
                    control_mode,
                    pid_kp,
                    pid_ki,
                    pid_kd,
                    consenso_pid_weight,
                    consenso_fuzzy_weight
                )
                SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM configuracion_control WHERE torre_id = %s
                )
                """,
                (
                    torre_id,
                    CONTROL_DEFAULTS["module_size_mm"],
                    CONTROL_DEFAULTS["deposito_litros"],
                    CONTROL_DEFAULTS["bomba_modelo"],
                    CONTROL_DEFAULTS["head_height_m"],
                    CONTROL_DEFAULTS["ph_min"],
                    CONTROL_DEFAULTS["ph_max"],
                    CONTROL_DEFAULTS["ec_min"],
                    CONTROL_DEFAULTS["ec_max"],
                    CONTROL_DEFAULTS["temperatura_agua_min"],
                    CONTROL_DEFAULTS["temperatura_agua_max"],
                    CONTROL_DEFAULTS["nivel_minimo"],
                    CONTROL_DEFAULTS["nivel_objetivo"],
                    CONTROL_DEFAULTS["irrigation_on_minutes"],
                    CONTROL_DEFAULTS["irrigation_off_minutes"],
                    CONTROL_DEFAULTS["control_mode"],
                    CONTROL_DEFAULTS["pid_kp"],
                    CONTROL_DEFAULTS["pid_ki"],
                    CONTROL_DEFAULTS["pid_kd"],
                    CONTROL_DEFAULTS["consenso_pid_weight"],
                    CONTROL_DEFAULTS["consenso_fuzzy_weight"],
                    torre_id,
                ),
            )

            for tipo, nombre in (
                ("bomba_principal", "Bomba principal"),
                ("valvula_agua", "Valvula de agua"),
                ("valvula_ab_mix", "Valvula AB Mix"),
                ("dosificador_ph", "Correccion de pH"),
            ):
                cursor.execute(
                    """
                    INSERT INTO actuadores_torre (torre_id, tipo, nombre)
                    SELECT %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM actuadores_torre WHERE torre_id = %s AND tipo = %s
                    )
                    """,
                    (torre_id, tipo, nombre, torre_id, tipo),
                )

            cursor.execute(
                """
                INSERT INTO programaciones_riego (
                    torre_id,
                    habilitado,
                    minutos_encendido,
                    minutos_apagado,
                    estrategia,
                    siguiente_ciclo
                )
                SELECT %s, TRUE, %s, %s, 'oxigenacion_radicular', 'inmediato'
                WHERE NOT EXISTS (
                    SELECT 1 FROM programaciones_riego WHERE torre_id = %s
                )
                """,
                (
                    torre_id,
                    CONTROL_DEFAULTS["irrigation_on_minutes"],
                    CONTROL_DEFAULTS["irrigation_off_minutes"],
                    torre_id,
                ),
            )
        connection.commit()
    finally:
        connection.close()


def _midpoint(minimum: float | int, maximum: float | int) -> float:
    return (float(minimum) + float(maximum)) / 2.0


def _fuzzy_output(error: float, span: float) -> float:
    if span <= 0:
        span = 1.0
    ratio = abs(error) / span
    if ratio < 0.15:
        base = 0.15
    elif ratio < 0.4:
        base = 0.45
    elif ratio < 0.75:
        base = 0.7
    else:
        base = 1.0
    return base if error >= 0 else -base


def _build_primary_control_event(config: dict, lectura: dict) -> dict:
    ph_target = _midpoint(config["ph_min"], config["ph_max"])
    ec_target = _midpoint(config["ec_min"], config["ec_max"])
    ph_value = lectura.get("ph")
    ec_value = lectura.get("ec")

    candidates: list[dict] = []
    if ph_value is not None:
        candidates.append(
            {
                "variable": "ph",
                "target": ph_target,
                "value": float(ph_value),
                "span": max(float(config["ph_max"]) - float(config["ph_min"]), 0.1),
            }
        )
    if ec_value is not None:
        candidates.append(
            {
                "variable": "ec",
                "target": ec_target,
                "value": float(ec_value),
                "span": max(float(config["ec_max"]) - float(config["ec_min"]), 0.1),
            }
        )

    if not candidates:
        return {
            "algoritmo": config["control_mode"],
            "variable_control": "sin_datos",
            "error_valor": 0.0,
            "salida_pid": 0.0,
            "salida_fuzzy": 0.0,
            "salida_consenso": 0.0,
            "accion_recomendada": "Mantener valvulas cerradas",
            "motivo": "No hay lecturas de pH o EC disponibles para calcular control.",
        }

    primary = max(candidates, key=lambda item: abs(item["target"] - item["value"]) / item["span"])
    error = primary["target"] - primary["value"]
    pid_output = float(config["pid_kp"] + config["pid_ki"] + config["pid_kd"]) * error
    fuzzy_output = _fuzzy_output(error, primary["span"])
    consensus_output = (
        float(config["consenso_pid_weight"]) * pid_output
        + float(config["consenso_fuzzy_weight"]) * fuzzy_output
    )

    if abs(error) < primary["span"] * 0.05:
        action = "Mantener valvulas cerradas"
        motivo = f"{primary['variable'].upper()} dentro de la ventana objetivo."
    elif primary["variable"] == "ec" and error > 0:
        action = "Dosificar AB Mix"
        motivo = "La conductividad esta por debajo del setpoint y requiere concentracion de nutrientes."
    elif primary["variable"] == "ec":
        action = "Diluir con agua"
        motivo = "La conductividad supera el setpoint y conviene reducir sales disueltas."
    elif error > 0:
        action = "Aplicar pH Up"
        motivo = "El pH esta por debajo del objetivo de operacion."
    else:
        action = "Aplicar pH Down"
        motivo = "El pH esta por encima del objetivo de operacion."

    return {
        "algoritmo": config["control_mode"],
        "variable_control": primary["variable"],
        "error_valor": round(error, 3),
        "salida_pid": round(pid_output, 3),
        "salida_fuzzy": round(fuzzy_output, 3),
        "salida_consenso": round(consensus_output, 3),
        "accion_recomendada": action,
        "motivo": motivo,
    }


def _upsert_alert(cursor, torre_id: int, tipo: str, severidad: str, mensaje: str, valor_actual, umbral: str) -> None:
    cursor.execute(
        """
        SELECT id_alerta
        FROM alertas_sistema
        WHERE torre_id = %s AND tipo = %s AND estado = 'activa'
        ORDER BY creada_en DESC, id_alerta DESC
        LIMIT 1
        """,
        (torre_id, tipo),
    )
    alerta = cursor.fetchone()
    if alerta:
        cursor.execute(
            """
            UPDATE alertas_sistema
            SET severidad = %s,
                mensaje = %s,
                valor_actual = %s,
                umbral_referencia = %s,
                creada_en = CURRENT_TIMESTAMP,
                cerrada_en = NULL
            WHERE id_alerta = %s
            """,
            (severidad, mensaje, valor_actual, umbral, alerta[0]),
        )
        return

    cursor.execute(
        """
        INSERT INTO alertas_sistema (torre_id, tipo, severidad, mensaje, valor_actual, umbral_referencia)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (torre_id, tipo, severidad, mensaje, valor_actual, umbral),
    )


def _close_alert(cursor, torre_id: int, tipo: str) -> None:
    cursor.execute(
        """
        UPDATE alertas_sistema
        SET estado = 'resuelta', cerrada_en = CURRENT_TIMESTAMP
        WHERE torre_id = %s AND tipo = %s AND estado = 'activa'
        """,
        (torre_id, tipo),
    )


def _record_control_state(torre_id: int, lectura_id: int, lectura: dict) -> None:
    _create_control_defaults_for_torre(torre_id)
    config = fetch_control_configuration(torre_id)
    if not config:
        return

    connection = _connect(include_database=True)
    try:
        with connection.cursor() as cursor:
            ph_value = lectura.get("ph")
            if ph_value is not None and (float(ph_value) < float(config["ph_min"]) or float(ph_value) > float(config["ph_max"])):
                _upsert_alert(
                    cursor,
                    torre_id,
                    "ph_fuera_rango",
                    "critica",
                    "pH fuera de la ventana segura para biodisponibilidad de nutrientes.",
                    ph_value,
                    f"{config['ph_min']}-{config['ph_max']}",
                )
            else:
                _close_alert(cursor, torre_id, "ph_fuera_rango")

            nivel_value = lectura.get("nivel_agua")
            if nivel_value is not None and float(nivel_value) <= float(config["nivel_minimo"]):
                _upsert_alert(
                    cursor,
                    torre_id,
                    "nivel_critico",
                    "critica",
                    "Nivel de deposito critico. Riesgo de cavitacion y trabajo en seco.",
                    nivel_value,
                    f"> {config['nivel_minimo']}",
                )
            else:
                _close_alert(cursor, torre_id, "nivel_critico")

            temperatura_agua = lectura.get("temperatura_agua")
            if temperatura_agua is not None and (
                float(temperatura_agua) < float(config["temperatura_agua_min"])
                or float(temperatura_agua) > float(config["temperatura_agua_max"])
            ):
                _upsert_alert(
                    cursor,
                    torre_id,
                    "temperatura_agua",
                    "media",
                    "Temperatura del agua fuera de la ventana de oxigenacion esperada.",
                    temperatura_agua,
                    f"{config['temperatura_agua_min']}-{config['temperatura_agua_max']}",
                )
            else:
                _close_alert(cursor, torre_id, "temperatura_agua")

            event = _build_primary_control_event(config, lectura)
            cursor.execute(
                """
                INSERT INTO eventos_control (
                    torre_id,
                    lectura_id,
                    algoritmo,
                    variable_control,
                    error_valor,
                    salida_pid,
                    salida_fuzzy,
                    salida_consenso,
                    accion_recomendada,
                    motivo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    torre_id,
                    lectura_id,
                    event["algoritmo"],
                    event["variable_control"],
                    event["error_valor"],
                    event["salida_pid"],
                    event["salida_fuzzy"],
                    event["salida_consenso"],
                    event["accion_recomendada"],
                    event["motivo"],
                ),
            )

            action = event["accion_recomendada"]
            valve_action = "cerrada"
            nutrient_action = "cerrada"
            ph_action = "en espera"
            if action == "Diluir con agua":
                valve_action = "abierta"
            elif action == "Dosificar AB Mix":
                nutrient_action = "activa"
            elif action in {"Aplicar pH Up", "Aplicar pH Down"}:
                ph_action = action

            cursor.execute(
                """
                UPDATE actuadores_torre
                SET estado = %s, ultimo_comando = %s
                WHERE torre_id = %s AND tipo = 'valvula_agua'
                """,
                (valve_action, action, torre_id),
            )
            cursor.execute(
                """
                UPDATE actuadores_torre
                SET estado = %s, ultimo_comando = %s
                WHERE torre_id = %s AND tipo = 'valvula_ab_mix'
                """,
                (nutrient_action, action, torre_id),
            )
            cursor.execute(
                """
                UPDATE actuadores_torre
                SET estado = %s, ultimo_comando = %s
                WHERE torre_id = %s AND tipo = 'dosificador_ph'
                """,
                (ph_action, action, torre_id),
            )
            cursor.execute(
                """
                UPDATE actuadores_torre
                SET estado = %s, ultimo_comando = %s
                WHERE torre_id = %s AND tipo = 'bomba_principal'
                """,
                ("activa" if lectura.get("nivel_agua") is None or float(lectura.get("nivel_agua")) > float(config["nivel_minimo"]) else "protegida", "Ciclo automatico 15/60", torre_id),
            )

        connection.commit()
    finally:
        connection.close()


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
    torre_id = _execute(
        """
        INSERT INTO torres (codigo_unico, nombre, ubicacion, usuario_id)
        VALUES (%s, %s, %s, %s)
        """,
        (codigo_unico.upper(), nombre, ubicacion, usuario_id),
    )
    _create_control_defaults_for_torre(torre_id)
    return torre_id


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
        _create_control_defaults_for_torre(existente["id_torre"])
        return existente["id_torre"]
    return insert_torre(codigo_normalizado, nombre, ubicacion, usuario_id)


def fetch_control_configuration(torre_id: int) -> dict | None:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    return _execute(
        "SELECT * FROM configuracion_control WHERE torre_id = %s LIMIT 1",
        (torre_id,),
        fetchone=True,
    )


def fetch_actuadores_by_torre(torre_id: int) -> list[dict]:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    return _execute(
        "SELECT * FROM actuadores_torre WHERE torre_id = %s ORDER BY id_actuador ASC",
        (torre_id,),
        fetchall=True,
    )


def fetch_irrigation_schedule(torre_id: int) -> dict | None:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    return _execute(
        "SELECT * FROM programaciones_riego WHERE torre_id = %s LIMIT 1",
        (torre_id,),
        fetchone=True,
    )


def fetch_active_alerts_by_torre(torre_id: int) -> list[dict]:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    return _execute(
        """
        SELECT *
        FROM alertas_sistema
        WHERE torre_id = %s AND estado = 'activa'
        ORDER BY FIELD(severidad, 'critica', 'alta', 'media', 'baja'), creada_en DESC, id_alerta DESC
        """,
        (torre_id,),
        fetchall=True,
    )


def fetch_recent_control_events(torre_id: int, limit: int = 6) -> list[dict]:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    return _execute(
        """
        SELECT *
        FROM eventos_control
        WHERE torre_id = %s
        ORDER BY creado_en DESC, id_evento DESC
        LIMIT %s
        """,
        (torre_id, limit),
        fetchall=True,
    )


def apply_assistant_control_action(
    torre_id: int,
    variable_control: str,
    accion_recomendada: str,
    motivo: str,
) -> None:
    create_mysql_tables()
    _create_control_defaults_for_torre(torre_id)
    config = fetch_control_configuration(torre_id)
    ultima_lectura = fetch_latest_sensor_reading_by_torre(torre_id)

    if config is None:
        raise ValueError("La torre no tiene configuracion de control disponible.")

    connection = _connect(include_database=True)
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                INSERT INTO eventos_control (
                    torre_id,
                    lectura_id,
                    algoritmo,
                    variable_control,
                    error_valor,
                    salida_pid,
                    salida_fuzzy,
                    salida_consenso,
                    accion_recomendada,
                    motivo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    torre_id,
                    ultima_lectura["id_lectura"] if ultima_lectura else None,
                    "ia_asistida",
                    variable_control,
                    0,
                    0,
                    0,
                    0,
                    accion_recomendada,
                    motivo,
                ),
            )

            valve_action = "cerrada"
            nutrient_action = "cerrada"
            ph_action = "en espera"
            pump_action = "activa"

            if accion_recomendada in {"Diluir con agua", "Recargar deposito"}:
                valve_action = "abierta"
            elif accion_recomendada == "Dosificar AB Mix":
                nutrient_action = "activa"
            elif accion_recomendada in {"Aplicar pH Up", "Aplicar pH Down"}:
                ph_action = accion_recomendada
            elif accion_recomendada == "Aumentar frecuencia de riego":
                cursor.execute(
                    """
                    UPDATE programaciones_riego
                    SET minutos_apagado = GREATEST(minutos_apagado - 10, 20),
                        estrategia = 'ajuste_ia_asistida',
                        siguiente_ciclo = 'adelantado'
                    WHERE torre_id = %s
                    """,
                    (torre_id,),
                )
            elif accion_recomendada == "Reducir frecuencia de riego":
                cursor.execute(
                    """
                    UPDATE programaciones_riego
                    SET minutos_apagado = LEAST(minutos_apagado + 10, 120),
                        estrategia = 'ajuste_ia_asistida',
                        siguiente_ciclo = 'diferido'
                    WHERE torre_id = %s
                    """,
                    (torre_id,),
                )

            if (
                ultima_lectura
                and ultima_lectura.get("nivel_agua") is not None
                and float(ultima_lectura["nivel_agua"]) <= float(config["nivel_minimo"])
            ):
                pump_action = "protegida"

            for actuator_type, actuator_state in (
                ("valvula_agua", valve_action),
                ("valvula_ab_mix", nutrient_action),
                ("dosificador_ph", ph_action),
                ("bomba_principal", pump_action),
            ):
                cursor.execute(
                    """
                    UPDATE actuadores_torre
                    SET estado = %s,
                        modo = 'asistido_ia',
                        ultimo_comando = %s
                    WHERE torre_id = %s AND tipo = %s
                    """,
                    (actuator_state, accion_recomendada, torre_id, actuator_type),
                )
        connection.commit()
    finally:
        connection.close()


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

    lectura_id = _execute(
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
    _record_control_state(
        torre["id_torre"],
        lectura_id,
        {
            "ph": ph,
            "ec": ec,
            "nivel_agua": nivel_agua,
            "temperatura_agua": temperatura_agua,
        },
    )
    return lectura_id


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
