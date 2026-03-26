import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager
from mysql.connector import Error

try:
    from Conexión import MYSQL_CONFIG, create_mysql_tables, fetch_mysql_usuario
    from blueprints import ai_bp, auth_bp, cultivos_bp, inventario_bp, main_bp, mysql_bp, sensores_bp, torres_bp
    from blueprints.shared import inventario, register_app_security, register_context_processors
    from inventario import init_app as init_db
    from models import User
except ModuleNotFoundError:
    from .Conexión import MYSQL_CONFIG, create_mysql_tables, fetch_mysql_usuario
    from .blueprints import ai_bp, auth_bp, cultivos_bp, inventario_bp, main_bp, mysql_bp, sensores_bp, torres_bp
    from .blueprints.shared import inventario, register_app_security, register_context_processors
    from .inventario import init_app as init_db
    from .models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Path(app.root_path) / 'inventario.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
app.config["SENSOR_API_TOKEN"] = os.environ.get("ECOGROW_SENSOR_API_TOKEN", "ecogrow-sensor-dev")

init_db(app)
with app.app_context():
    inventario.sync_files()

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

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(torres_bp)
app.register_blueprint(cultivos_bp)
app.register_blueprint(sensores_bp)
app.register_blueprint(mysql_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(ai_bp)


@app.cli.command("sincronizar-datos")
def sincronizar_datos():
    inventario.sync_files()
    print("Archivos TXT, JSON y CSV sincronizados desde SQLite.")


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
