"""Mobile adapter for the existing schema; no migrations or device credentials.

Legacy actuator rows mix commands and reports. They cannot establish physical
confirmation. Tank capacity is an uncalibrated default, not a volume measurement.
"""
import json
import math
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash

try:
    from Conexión.conexion import _execute, _execute_transaction
    from domain.hidroponia_torre import merge_control_with_phase_profile
except ModuleNotFoundError:
    from ..Conexión.conexion import _execute, _execute_transaction
    from ..domain.hidroponia_torre import merge_control_with_phase_profile

STALE_SECONDS = 120


def create_pump_command(tower_id, desired_state, ttl_sec=60):
    now = int(time.time())
    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    action = "PUMP_ON" if desired_state == "on" else "PUMP_OFF"
    cmd = {
        "id": cmd_id,
        "action": action,
        "desired": desired_state,
        "created_at": now,
        "expires_at": now + ttl_sec,
        "ttl_sec": ttl_sec,
        "status": "pending",
    }
    try:
        _execute_transaction([
            (
                "UPDATE dispositivo_comandos SET estado='superseded' WHERE torre_id=%s AND estado='pending'",
                (tower_id,),
            ),
            (
                """INSERT INTO dispositivo_comandos (id_comando, torre_id, accion, estado_deseado, parametros_json, estado, creado_en, expira_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (cmd_id, tower_id, action, desired_state, None, "pending", now, now + ttl_sec),
            ),
        ])
    except Exception as exc:
        raise MobileError("command_storage_failed", f"No se pudo persistir la orden en base de datos: {exc}", 503) from exc
    return cmd


def create_mode_command(tower_id, mode, ttl_sec=60):
    now = int(time.time())
    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    mode_clean = str(mode).strip().upper()
    cmd = {
        "id": cmd_id,
        "action": "SET_MODE",
        "mode": mode_clean,
        "desired": mode_clean,
        "created_at": now,
        "expires_at": now + ttl_sec,
        "ttl_sec": ttl_sec,
        "status": "pending",
    }
    try:
        _execute_transaction([
            (
                "UPDATE dispositivo_comandos SET estado='superseded' WHERE torre_id=%s AND estado='pending'",
                (tower_id,),
            ),
            (
                """INSERT INTO dispositivo_comandos (id_comando, torre_id, accion, estado_deseado, parametros_json, estado, creado_en, expira_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (cmd_id, tower_id, "SET_MODE", mode_clean, json.dumps({"mode": mode_clean}), "pending", now, now + ttl_sec),
            ),
        ])
    except Exception as exc:
        raise MobileError("command_storage_failed", f"No se pudo persistir la orden en base de datos: {exc}", 503) from exc
    return cmd


def create_recipe_command(tower_id, recipe_idx, ttl_sec=60):
    now = int(time.time())
    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    cmd = {
        "id": cmd_id,
        "action": "SET_RECIPE",
        "recipe_idx": int(recipe_idx),
        "desired": str(recipe_idx),
        "created_at": now,
        "expires_at": now + ttl_sec,
        "ttl_sec": ttl_sec,
        "status": "pending",
    }
    try:
        _execute_transaction([
            (
                "UPDATE dispositivo_comandos SET estado='superseded' WHERE torre_id=%s AND estado='pending'",
                (tower_id,),
            ),
            (
                """INSERT INTO dispositivo_comandos (id_comando, torre_id, accion, estado_deseado, parametros_json, estado, creado_en, expira_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (cmd_id, tower_id, "SET_RECIPE", str(recipe_idx), json.dumps({"recipe_idx": int(recipe_idx)}), "pending", now, now + ttl_sec),
            ),
        ])
    except Exception as exc:
        raise MobileError("command_storage_failed", f"No se pudo persistir la orden en base de datos: {exc}", 503) from exc
    return cmd


def get_active_command(tower_id):
    now = int(time.time())
    # Deterministic query: pending command first, then latest overall by (creado_en DESC, id_comando DESC)
    row = _execute(
        "SELECT * FROM dispositivo_comandos WHERE torre_id=%s AND estado='pending' ORDER BY creado_en DESC, id_comando DESC LIMIT 1",
        (tower_id,),
        fetchone=True,
    )
    if not row:
        row = _execute(
            "SELECT * FROM dispositivo_comandos WHERE torre_id=%s ORDER BY creado_en DESC, id_comando DESC LIMIT 1",
            (tower_id,),
            fetchone=True,
        )
    if not row:
        return None

    cmd_status = row.get("estado", "pending")
    exp = int(row.get("expira_en", 0))
    if cmd_status == "pending" and now >= exp:
        cmd_status = "expired"
        try:
            _execute("UPDATE dispositivo_comandos SET estado='expired' WHERE id_comando=%s AND torre_id=%s", (row["id_comando"], tower_id))
        except Exception:
            pass

    params = {}
    if row.get("parametros_json"):
        try:
            params = json.loads(row["parametros_json"])
        except Exception:
            pass

    return {
        "id": row["id_comando"],
        "action": row["accion"],
        "desired": row["estado_deseado"],
        "created_at": int(row["creado_en"]),
        "expires_at": exp,
        "ttl_sec": max(0, exp - int(row["creado_en"])),
        "status": cmd_status,
        **params,
    }


def get_active_pump_command(tower_id):
    now = int(time.time())
    row = _execute(
        "SELECT * FROM dispositivo_comandos WHERE torre_id=%s AND accion IN ('PUMP_ON', 'PUMP_OFF') "
        "ORDER BY creado_en DESC, id_comando DESC LIMIT 1",
        (tower_id,),
        fetchone=True,
    )
    if not row:
        return None

    cmd_status = row.get("estado", "pending")
    exp = int(row.get("expira_en", 0))
    if cmd_status == "pending" and now >= exp:
        cmd_status = "expired"
        try:
            _execute("UPDATE dispositivo_comandos SET estado='expired' WHERE id_comando=%s AND torre_id=%s", (row["id_comando"], tower_id))
        except Exception:
            pass

    params = {}
    if row.get("parametros_json"):
        try:
            params = json.loads(row["parametros_json"])
        except Exception:
            pass

    return {
        "id": row["id_comando"],
        "action": row["accion"],
        "desired": row["estado_deseado"],
        "created_at": int(row["creado_en"]),
        "expires_at": exp,
        "ttl_sec": max(0, exp - int(row["creado_en"])),
        "status": cmd_status,
        **params,
    }


def record_command_ack(tower_id, cmd_id, ack_status):
    """Confirms command execution/rejection for the authenticated tower.

    Validates:
    - cmd_id is provided, non-empty, and valid string
    - ack_status is an allowed target status ('executed', 'rejected', 'expired')
    - The command belongs to tower_id and is currently in 'pending' state
    Rejects foreign tower commands and refuses wildcard updates.
    """
    if not cmd_id or not isinstance(cmd_id, str) or not str(cmd_id).strip():
        return None

    clean_cmd_id = str(cmd_id).strip()
    now = int(time.time())
    normalized = str(ack_status).lower()

    if "executed" in normalized or "ok" in normalized:
        status_val = "executed"
    elif "expired" in normalized:
        status_val = "expired"
    elif "reject" in normalized:
        status_val = "rejected"
    else:
        return None

    # Check ownership and pending state
    row = _execute(
        "SELECT id_comando, torre_id, accion, estado_deseado, parametros_json, estado, creado_en, expira_en "
        "FROM dispositivo_comandos WHERE id_comando=%s AND torre_id=%s LIMIT 1",
        (clean_cmd_id, tower_id),
        fetchone=True,
    )
    if not row or row.get("estado") != "pending":
        return None

    _execute(
        "UPDATE dispositivo_comandos SET estado=%s, ejecutado_en=%s, ack_mensaje=%s "
        "WHERE id_comando=%s AND torre_id=%s AND estado='pending'",
        (status_val, now, str(ack_status)[:255], clean_cmd_id, tower_id),
    )

    params = {}
    if row.get("parametros_json"):
        try:
            params = json.loads(row["parametros_json"])
        except Exception:
            pass

    return {
        "id": row["id_comando"],
        "action": row["accion"],
        "desired": row["estado_deseado"],
        "created_at": int(row["creado_en"]),
        "expires_at": int(row["expira_en"]),
        "ttl_sec": max(0, int(row["expira_en"]) - int(row["creado_en"])),
        "status": status_val,
        **params,
    }


class MobileError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def authenticate(mail, password):
    row = _execute("SELECT * FROM usuarios WHERE mail = %s LIMIT 1", (mail,), fetchone=True)
    stored = str(row.get("password", "")) if row else ""
    if stored.startswith(("scrypt:", "pbkdf2:")):
        valid = check_password_hash(stored, password)
    else:
        valid = bool(stored) and secrets.compare_digest(stored.encode(), password.encode())
    return row if row and valid else None


def user_by_id(user_id):
    return _execute("SELECT * FROM usuarios WHERE id_usuario = %s", (user_id,), fetchone=True)


def tower_summary(row):
    return {"id": row["id_torre"], "name": row["nombre"], "code": row["codigo_unico"]}


def bind_tower(user_id: int, code: str, name: str = "", location: str = ""):
    if not code or not isinstance(code, str) or not code.strip():
        raise MobileError("invalid_payload", "El código único de la torre es obligatorio.", 400)
    clean_code = str(code).strip().upper()
    if len(clean_code) < 3 or len(clean_code) > 64:
        raise MobileError("invalid_payload", "El código de la torre debe tener entre 3 y 64 caracteres.", 400)
    clean_name = str(name).strip()[:100] if name else f"Torre {clean_code[-4:]}"
    clean_loc = str(location).strip()[:100] if location else ""

    try:
        from Conexión.conexion import register_torre, fetch_torre
    except ModuleNotFoundError:
        from ..Conexión.conexion import register_torre, fetch_torre

    try:
        tower_id = register_torre(clean_code, clean_name, clean_loc, user_id)
    except ValueError as exc:
        raise MobileError("tower_already_claimed", str(exc), 409) from exc
    except Exception as exc:
        raise MobileError("storage_failed", f"No se pudo vincular la torre: {exc}", 500) from exc

    row = fetch_torre(tower_id)
    return tower_summary(row) if row else {"id": tower_id, "name": clean_name, "code": clean_code}


def list_towers(user_id):
    rows = _execute("SELECT id_torre, nombre, codigo_unico FROM torres WHERE usuario_id = %s AND estado <> 'inactivo' ORDER BY id_torre", (user_id,), fetchall=True)
    return [tower_summary(row) for row in rows]


def owned_tower(tower_id, user_id):
    row = _execute("SELECT id_torre, nombre, codigo_unico, estado FROM torres WHERE id_torre = %s AND usuario_id = %s", (tower_id, user_id), fetchone=True)
    if not row:
        raise MobileError("tower_not_found", "Torre no disponible para esta cuenta.", 404)
    return row


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def timestamp(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    # Existing MySQL TIMESTAMP values are naive; connection uses server session
    # timezone. Do not invent a UTC offset. Emit naive ISO unless provided.
    return value.isoformat()


def is_stale(value, now=None):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return True
    if not isinstance(value, datetime) or value.tzinfo is None:
        # MySQL session time is normalized at query time with UTC_TIMESTAMP;
        # raw naive values outside that path are not trusted for commands.
        return True
    age = ((now or datetime.now(timezone.utc)) - value).total_seconds()
    return age < 0 or age > STALE_SECONDS


def readings(tower_id, limit=20):
    # TIMESTAMP auto conversion is session-dependent. Derive age in MySQL to
    # express the reading time relative to UTC independently of that timezone.
    rows = _execute("""SELECT l.*, TIMESTAMPDIFF(SECOND, l.fecha_registro, CURRENT_TIMESTAMP) AS age_seconds
        FROM lecturas_sensores l JOIN ciclos_cultivo c ON c.id_ciclo=l.ciclo_id
        WHERE c.torre_id=%s ORDER BY l.fecha_registro DESC, l.id_lectura DESC LIMIT %s""", (tower_id, limit), fetchall=True)
    for row in rows:
        age = finite(row.get("age_seconds"))
        if age is not None:
            row["utc_reading_time"] = datetime.now(timezone.utc) - timedelta(seconds=age)
    return rows


def reading_timestamp(row):
    return row.get("utc_reading_time") if row else None


def sensors(row):
    row = row or {}
    level = finite(row.get("nivel_agua"))
    liters = finite(row.get("volumen_litros")) if row.get("volumen_litros") is not None else finite(row.get("litros"))
    return {"ph": finite(row.get("ph")), "tds_ppm": finite(row.get("tds_ppm")),
            "ec_ms_cm": finite(row.get("ec")),
            "nivel_pct": level if level is not None and 0 <= level <= 100 else None,
            "litros": liters, "temperatura_agua_c": finite(row.get("temperatura_agua"))}


def configuration(tower_id):
    return _execute("SELECT * FROM configuracion_control WHERE torre_id=%s", (tower_id,), fetchone=True)


def pump_row(tower_id):
    return _execute("SELECT estado, modo, ultimo_comando FROM actuadores_torre WHERE torre_id=%s AND tipo='bomba_principal'", (tower_id,), fetchone=True)


def irrigation_row(tower_id):
    return _execute("SELECT * FROM programaciones_riego WHERE torre_id=%s", (tower_id,), fetchone=True)


def irrigation_payload(row):
    return {"enabled": bool(row["habilitado"]), "on_minutes": row["minutos_encendido"], "off_minutes": row["minutos_apagado"], "strategy": row["estrategia"]} if row else None


def tower_detail(tower_id, user_id):
    tower = owned_tower(tower_id, user_id)
    history = readings(tower_id)
    latest = history[0] if history else {}
    pump = pump_row(tower_id)
    irrigation = irrigation_row(tower_id)
    cycle = _execute("""SELECT c.id_ciclo,c.fase,c.notas,u.nombre AS cultivo_nombre FROM ciclos_cultivo c
        JOIN cultivos u ON u.id_cultivo=c.cultivo_id WHERE c.torre_id=%s AND c.estado='activo' ORDER BY c.id_ciclo DESC LIMIT 1""", (tower_id,), fetchone=True)
    alerts = _execute("SELECT id_alerta,severidad,mensaje,creada_en FROM alertas_sistema WHERE torre_id=%s AND estado='activa' ORDER BY creada_en DESC LIMIT 50", (tower_id,), fetchall=True)
    events = _execute("SELECT id_evento,accion_recomendada,motivo,creado_en FROM eventos_control WHERE torre_id=%s ORDER BY creado_en DESC LIMIT 20", (tower_id,), fetchall=True)
    config = configuration(tower_id)
    inactive = tower.get("estado") == "inactivo"

    active_pump_cmd = get_active_pump_command(tower_id)
    physical_reported = (
        {"encendida": "on", "apagada": "off"}.get(pump.get("estado"))
        if pump and str(pump.get("ultimo_comando", "")).startswith("reporte_")
        else None
    )

    if active_pump_cmd:
        desired = active_pump_cmd["desired"] if active_pump_cmd["desired"] in ("on", "off") else None
        cmd_status = active_pump_cmd["status"]
        if physical_reported in ("on", "off"):
            reported = physical_reported
        else:
            reported = None
        pump_cmd_id = active_pump_cmd["id"]
        pump_cmd_exp = active_pump_cmd["expires_at"]
    else:
        desired = {"encendida": "on", "apagada": "off"}.get(pump.get("estado")) if pump else None
        reported = physical_reported
        cmd_status = "pending" if pump and pump.get("ultimo_comando") == "mobile_dashboard" else "unconfirmed" if pump else "unknown"
        pump_cmd_id = None
        pump_cmd_exp = None

    effective = merge_control_with_phase_profile(config, cycle["fase"], cycle["cultivo_nombre"]) if config and cycle else config
    return {**tower_summary(tower), "source": "remote", "sensors": sensors(latest),
        "updated_at": timestamp(reading_timestamp(latest)), "stale": is_stale(reading_timestamp(latest)),
        "pump": {
            "desired": desired,
            "reported": reported,
            "mode": "AUTO" if pump and (pump.get("modo") in ("automatico", "AUTO")) else "MANUAL" if pump and (pump.get("modo") in ("manual", "MANUAL")) else (pump.get("modo") if pump else None),
            "status": cmd_status,
            "command_id": pump_cmd_id,
            "expires_at": pump_cmd_exp,
        },
        "irrigation": irrigation_payload(irrigation),
        "cycle": {"id": cycle["id_ciclo"], "phase": cycle["fase"], "crop": cycle["cultivo_nombre"]} if cycle else None,
        "recipe": {"phase": cycle["fase"], "crop": cycle["cultivo_nombre"], "notes": effective.get("perfil_notas", "") if effective else ""} if cycle else None,
        "alerts": [{"id": r["id_alerta"], "severity": r["severidad"], "message": r["mensaje"], "created_at": timestamp(r["creada_en"])} for r in alerts],
        "events": [{"id": r["id_evento"], "action": r["accion_recomendada"], "reason": r["motivo"], "created_at": timestamp(r["creado_en"])} for r in events],
        "history": [{"updated_at": timestamp(reading_timestamp(r)), "sensors": sensors(r)} for r in history],
        "capabilities": {
            "pump_control": bool(pump) and not inactive,
            "mode_control": bool(pump) and not inactive,
            "irrigation_edit": bool(irrigation) and not inactive,
            "recipe_edit": not inactive,
            "local_connection": False,
            "tds": True,
            "liters": bool(config and config.get("deposito_calibrado") and config.get("deposito_litros")),
            "pump_reported": reported is not None,
        }}


def command_pump(tower_id, user_id, state):
    tower = owned_tower(tower_id, user_id)
    if tower.get("estado") == "inactivo" or not pump_row(tower_id):
        raise MobileError("control_unavailable", "Control no disponible para esta torre.", 409)
    if state == "on":
        history = readings(tower_id, 1)
        latest = history[0] if history else {}
        if is_stale(reading_timestamp(latest)):
            raise MobileError("stale_reading", "Se requiere una lectura reciente para encender.", 409)
        level = sensors(latest)["nivel_pct"]
        config = configuration(tower_id) or {}
        minimum = finite(config.get("nivel_minimo"))
        if level is None or minimum is None or not 0 <= minimum < 100 or level <= minimum:
            raise MobileError("unsafe_level", "Nivel de agua inválido o insuficiente.", 409)
    cmd = create_pump_command(tower_id, state)
    _execute("""UPDATE actuadores_torre SET estado=%s,modo='manual',ultimo_comando='mobile_dashboard',actualizado_en=CURRENT_TIMESTAMP
        WHERE torre_id=%s AND tipo='bomba_principal'""", ("encendida" if state == "on" else "apagada", tower_id))
    return {"accepted": True, "desired": state, "reported": None, "status": "pending",
            "command_id": cmd["id"], "expires_at": cmd["expires_at"],
            "message": "Orden guardada; falta confirmación del dispositivo."}


def command_mode(tower_id, user_id, mode):
    tower = owned_tower(tower_id, user_id)
    if tower.get("estado") == "inactivo":
        raise MobileError("control_unavailable", "Control no disponible para esta torre.", 409)
    mode_clean = str(mode).strip().upper()
    if mode_clean not in {"AUTO", "MANUAL"}:
        raise MobileError("invalid_payload", "Modo debe ser 'AUTO' o 'MANUAL'.", 400)
    cmd = create_mode_command(tower_id, mode_clean)
    _execute(
        "UPDATE actuadores_torre SET modo=%s, ultimo_comando='mobile_dashboard', actualizado_en=CURRENT_TIMESTAMP WHERE torre_id=%s AND tipo='bomba_principal'",
        ("automatico" if mode_clean == "AUTO" else "manual", tower_id),
    )
    return {
        "accepted": True,
        "desired": mode_clean,
        "status": "pending",
        "command_id": cmd["id"],
        "expires_at": cmd["expires_at"],
        "message": f"Modo {mode_clean} solicitado; esperando confirmación del dispositivo.",
    }


def command_recipe(tower_id, user_id, recipe_idx):
    tower = owned_tower(tower_id, user_id)
    if tower.get("estado") == "inactivo":
        raise MobileError("control_unavailable", "Control no disponible para esta torre.", 409)
    try:
        r_idx = int(recipe_idx)
        if not (0 <= r_idx <= 3):
            raise ValueError()
    except (ValueError, TypeError):
        raise MobileError("invalid_payload", "Índice de receta inválido (0 a 3).", 400)
    cmd = create_recipe_command(tower_id, r_idx)
    return {
        "accepted": True,
        "desired": str(r_idx),
        "status": "pending",
        "command_id": cmd["id"],
        "expires_at": cmd["expires_at"],
        "message": f"Receta {r_idx} solicitada; esperando confirmación del dispositivo.",
    }


def save_irrigation(tower_id, user_id, payload):
    tower = owned_tower(tower_id, user_id)
    existing = irrigation_row(tower_id)
    if tower.get("estado") == "inactivo" or not existing:
        raise MobileError("control_unavailable", "Programación no disponible.", 409)
    enabled = payload.get("enabled")
    on_minutes, off_minutes = payload.get("on_minutes"), payload.get("off_minutes")
    if not isinstance(enabled, bool) or any(type(v) is not int or not 1 <= v <= 1440 for v in (on_minutes, off_minutes)):
        raise MobileError("invalid_payload", "Indica habilitación y minutos entre 1 y 1440.")
    _execute("UPDATE programaciones_riego SET habilitado=%s,minutos_encendido=%s,minutos_apagado=%s,actualizado_en=CURRENT_TIMESTAMP WHERE torre_id=%s", (enabled, on_minutes, off_minutes, tower_id))
    return {"accepted": True, "status": "saved", "message": "Programación guardada en servidor; no acredita aplicación en dispositivo.", "irrigation": {"enabled": enabled, "on_minutes": on_minutes, "off_minutes": off_minutes, "strategy": existing["estrategia"]}}
