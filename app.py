import os
import secrets

from flask import Flask, flash, redirect, request, url_for
from flask_login import LoginManager
from mysql.connector import Error

try:
    from Conexión import MYSQL_CONFIG, create_mysql_tables, fetch_mysql_usuario
    from blueprints import ai_bp, auth_bp, cultivos_bp, main_bp, mysql_bp, sensores_bp, torres_bp
    from blueprints.shared import register_app_security, register_context_processors
    from models import User
except ModuleNotFoundError:
    from .Conexión import MYSQL_CONFIG, create_mysql_tables, fetch_mysql_usuario
    from .blueprints import ai_bp, auth_bp, cultivos_bp, main_bp, mysql_bp, sensores_bp, torres_bp
    from .blueprints.shared import register_app_security, register_context_processors
    from .models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
sensor_api_token = os.environ.get("ECOGROW_SENSOR_API_TOKEN", "").strip()
app.config["SENSOR_API_TOKEN"] = sensor_api_token or secrets.token_urlsafe(32)
app.config["SENSOR_API_TOKEN_CONFIGURED"] = bool(sensor_api_token)
app.config["ADMIN_EMAILS"] = {
    email.strip().lower()
    for email in os.environ.get("ECOGROW_ADMIN_EMAILS", "").split(",")
    if email.strip()
}

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesion para acceder al panel de gestion."
login_manager.login_message_category = "error"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return User.from_mysql_row(fetch_mysql_usuario(int(user_id)))
    except (Error, ValueError):
        return None


@login_manager.unauthorized_handler
def unauthorized():
    flash("Inicia sesion para acceder al panel de gestion.", "error")
    return redirect(url_for("auth.login"))


register_app_security(app)
register_context_processors(app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ecogrow"}, 200


@app.after_request
def apply_response_headers(response):
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy-Report-Only",
        (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        ),
    )
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(torres_bp)
app.register_blueprint(cultivos_bp)
app.register_blueprint(sensores_bp)
app.register_blueprint(mysql_bp)
app.register_blueprint(ai_bp)


@app.cli.command("mysql-init")
def mysql_init():
    try:
        create_mysql_tables()
        print("MySQL inicializado correctamente.")
        print(
            f"Host: {MYSQL_CONFIG['host']} | "
            f"Usuario: {MYSQL_CONFIG['user']} | "
            f"Base de datos: {MYSQL_CONFIG['database']}"
        )
        print(f"Puerto: {MYSQL_CONFIG['port']} | Socket: {MYSQL_CONFIG['unix_socket']}")
    except Error as exc:
        print(f"No se pudo inicializar MySQL: {exc}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
