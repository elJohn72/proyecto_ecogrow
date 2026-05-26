import secrets
from functools import wraps

from flask import current_app, flash, redirect, request, session, url_for
from flask_login import current_user, login_required as flask_login_required
from mysql.connector import Error

try:
    from Conexión import fetch_torre
except ModuleNotFoundError:
    from ..Conexión import fetch_torre

login_required = flask_login_required


def is_admin_user() -> bool:
    if not current_user.is_authenticated:
        return False
    admin_emails = current_app.config.get("ADMIN_EMAILS", set())
    return current_user.mail.strip().lower() in admin_emails


def is_admin_mode() -> bool:
    return is_admin_user() and session.get("ui_mode", "user") == "admin"


def current_user_id() -> int | None:
    if not current_user.is_authenticated:
        return None
    return int(current_user.get_id())


def current_torre():
    torre_id = session.get("torre_id")
    if not torre_id:
        return None
    try:
        torre = fetch_torre(int(torre_id))
        if torre and str(torre.get("estado", "")).lower() == "inactivo":
            session.pop("torre_id", None)
            return None
        return torre
    except Error:
        return None


def tower_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Inicia sesion para acceder al panel de gestion.", "error")
            return redirect(url_for("auth.login"))

        torre = current_torre()
        if not torre:
            flash("Primero registra o selecciona tu torre hidropónica.", "error")
            return redirect(url_for("torres.torres"))

        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Inicia sesion para acceder al panel de gestion.", "error")
            return redirect(url_for("auth.login"))

        if not is_admin_user():
            flash("Cambia al modo administrador para realizar esta accion.", "error")
            return redirect(request.referrer or url_for("torres.dashboard"))

        return view(*args, **kwargs)

    return wrapped_view


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def is_valid_csrf_token(token: str | None) -> bool:
    return bool(token) and token == session.get("csrf_token")


def register_app_security(app):
    @app.before_request
    def protect_forms():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        if request.endpoint in {"sensores.api_sensor_reading", "sensores.api_iot_sync"}:
            return None

        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if is_valid_csrf_token(token):
            return None

        flash("La sesion del formulario vencio. Intenta nuevamente.", "error")
        return redirect(request.referrer or url_for("main.inicio"))


def register_context_processors(app):
    @app.context_processor
    def inject_layout_state():
        torre = current_torre() if current_user.is_authenticated else None
        admin_user = is_admin_user()
        if admin_user:
            ui_mode = session.get("ui_mode", "user")
            if ui_mode not in {"user", "admin"}:
                ui_mode = "user"
        else:
            ui_mode = "user"
            if session.get("ui_mode") == "admin":
                session["ui_mode"] = "user"

        return {
            "is_authenticated": current_user.is_authenticated,
            "current_user_name": current_user.nombre if current_user.is_authenticated else None,
            "current_torre": torre,
            "csrf_token": get_csrf_token,
            "can_manage": current_user.is_authenticated,
            "is_admin": admin_user,
            "is_admin_mode": admin_user and ui_mode == "admin",
            "ui_mode": ui_mode,
        }


def parse_optional_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Uno de los valores numericos del sensor no es valido.") from exc
