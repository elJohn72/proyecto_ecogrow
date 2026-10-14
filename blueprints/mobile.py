"""Session-authenticated JSON surface for mobile and Android clients."""
import secrets
import time
from functools import wraps
from threading import Lock

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_user, logout_user
from mysql.connector import Error

try:
    from models import User
    from services import mobile_service as service
except ModuleNotFoundError:
    from ..models import User
    from ..services import mobile_service as service
from .shared import get_csrf_token

mobile_bp = Blueprint("mobile", __name__, url_prefix="/api/mobile")
_attempts = {}
_attempt_lock = Lock()


def error(code, message, status):
    return jsonify(error=code, message=message), status


def authenticated(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return error("auth_required", "Inicia sesión para continuar.", 401)
        return view(*args, **kwargs)
    return wrapper


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise service.MobileError("invalid_payload", "Se requiere un objeto JSON.")
    return data


def session_payload():
    user = {"id": int(current_user.get_id()), "name": current_user.nombre, "mail": current_user.mail} if current_user.is_authenticated else None
    return {"authenticated": bool(user), "user": user, "csrf_token": get_csrf_token()}


@mobile_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@mobile_bp.errorhandler(service.MobileError)
def mobile_error(exc):
    return error(exc.code, exc.message, exc.status)


@mobile_bp.errorhandler(Error)
def database_error(_exc):
    return error("service_unavailable", "Servicio temporalmente no disponible.", 503)


@mobile_bp.get("/session")
def get_session():
    return jsonify(session_payload())


@mobile_bp.post("/register")
def register():
    data = payload()
    name = data.get("name")
    mail = data.get("mail")
    password = data.get("password")
    password_confirm = data.get("password_confirm")

    key, now = request.remote_addr or "unknown", time.monotonic()
    with _attempt_lock:
        for address in list(_attempts):
            _attempts[address] = [t for t in _attempts[address] if now - t < 60]
            if not _attempts[address]:
                del _attempts[address]
        if len(_attempts) >= 4096 and key not in _attempts:
            return error("rate_limited", "Espera un minuto antes de reintentar.", 429)
        recent = _attempts.setdefault(key, [])
        if len(recent) >= 10:
            return error("rate_limited", "Espera un minuto antes de reintentar.", 429)
        recent.append(now)

    user_dict = service.register_user(name, mail, password, password_confirm)
    session.clear()
    session["csrf_token"] = secrets.token_urlsafe(32)
    login_user(User(user_dict["id_usuario"], user_dict["nombre"], user_dict["mail"]))
    return jsonify(session_payload()), 201


@mobile_bp.post("/login")
def login():
    data = payload()
    mail, password = data.get("mail"), data.get("password")
    if not isinstance(mail, str) or not isinstance(password, str) or not mail.strip() or not password or len(mail) > 254 or len(password) > 1024:
        raise service.MobileError("invalid_payload", "Indica correo y contraseña válidos.")
    # Remote address is authoritative; untrusted X-Forwarded-For is not used.
    key, now = request.remote_addr or "unknown", time.monotonic()
    with _attempt_lock:
        for address in list(_attempts):
            _attempts[address] = [t for t in _attempts[address] if now - t < 60]
            if not _attempts[address]:
                del _attempts[address]
        if len(_attempts) >= 4096 and key not in _attempts:
            return error("rate_limited", "Espera un minuto antes de reintentar.", 429)
        recent = _attempts.setdefault(key, [])
        if len(recent) >= 10:
            return error("rate_limited", "Espera un minuto antes de reintentar.", 429)
        recent.append(now)
    row = service.authenticate(mail.strip(), password)
    if not row:
        return error("invalid_credentials", "Credenciales incorrectas.", 401)
    session.clear()
    session["csrf_token"] = secrets.token_urlsafe(32)
    login_user(User.from_mysql_row(row))
    return jsonify(session_payload())


@mobile_bp.post("/logout")
@authenticated
def logout():
    logout_user()
    session.clear()
    return jsonify(session_payload())


@mobile_bp.post("/towers/bind")
@authenticated
def bind_tower():
    data = payload()
    code = data.get("code")
    pop = data.get("pop", "")
    name = data.get("name", "")
    location = data.get("location", "")
    tower_info = service.bind_tower(int(current_user.get_id()), code, pop, name, location)
    return jsonify(ok=True, tower=tower_info, message="Torre vinculada exitosamente a tu cuenta."), 201


@mobile_bp.get("/towers")
@authenticated
def towers():
    return jsonify(towers=service.list_towers(int(current_user.get_id())))


@mobile_bp.get("/towers/<int:tower_id>")
@authenticated
def tower(tower_id):
    return jsonify(service.tower_detail(tower_id, int(current_user.get_id())))


@mobile_bp.post("/towers/<int:tower_id>/pump")
@authenticated
def pump(tower_id):
    data = payload()
    state = data.get("state")
    if state not in ("on", "off"):
        raise service.MobileError("invalid_payload", "Estado permitido: on u off.")
    return jsonify(service.command_pump(tower_id, int(current_user.get_id()), state)), 202


@mobile_bp.post("/towers/<int:tower_id>/irrigation")
@authenticated
def irrigation(tower_id):
    return jsonify(service.save_irrigation(tower_id, int(current_user.get_id()), payload()))


@mobile_bp.post("/towers/<int:tower_id>/mode")
@authenticated
def mode(tower_id):
    data = payload()
    m = data.get("mode")
    if not m:
        raise service.MobileError("invalid_payload", "Indica el modo: AUTO o MANUAL.")
    return jsonify(service.command_mode(tower_id, int(current_user.get_id()), m)), 202


@mobile_bp.post("/towers/<int:tower_id>/recipe")
@authenticated
def recipe(tower_id):
    data = payload()
    r = data.get("recipe_idx")
    if r is None:
        raise service.MobileError("invalid_payload", "Indica el índice de receta (recipe_idx).")
    return jsonify(service.command_recipe(tower_id, int(current_user.get_id()), r)), 202
