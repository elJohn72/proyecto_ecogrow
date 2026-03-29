import secrets
from functools import wraps

from flask import flash, redirect, request, session, url_for
from flask_login import current_user, login_required as flask_login_required
from mysql.connector import Error

try:
    from Conexión import fetch_torre
except ModuleNotFoundError:
    from ..Conexión import fetch_torre

login_required = flask_login_required


def current_user_id() -> int | None:
    if not current_user.is_authenticated:
        return None
    return int(current_user.get_id())


def current_torre():
    torre_id = session.get("torre_id")
    if not torre_id:
        return None
    try:
        return fetch_torre(int(torre_id))
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

        if request.endpoint == "sensores.api_sensor_reading":
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
        ui_mode = session.get("ui_mode", "user") if current_user.is_authenticated else "user"
        return {
            "is_authenticated": current_user.is_authenticated,
            "current_user_name": current_user.nombre if current_user.is_authenticated else None,
            "current_torre": torre,
            "csrf_token": get_csrf_token,
            "ui_mode": ui_mode,
        }


def parse_optional_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Uno de los valores numericos del sensor no es valido.") from exc
