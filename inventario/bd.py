from pathlib import Path
import sqlite3

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
TXT_FILE = DATA_DIR / "datos.txt"
JSON_FILE = DATA_DIR / "datos.json"
CSV_FILE = DATA_DIR / "datos.csv"


def init_app(app) -> None:
    db.init_app(app)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for data_file in (TXT_FILE, JSON_FILE, CSV_FILE):
        if not data_file.exists():
            data_file.write_text("" if data_file.suffix != ".json" else "[]", encoding="utf-8")

    from .productos import Producto  # noqa: F401

    with app.app_context():
        db.create_all()
        _ensure_productos_schema(app.config["SQLALCHEMY_DATABASE_URI"])


def _ensure_productos_schema(database_uri: str) -> None:
    if not database_uri.startswith("sqlite:///"):
        return

    db_path = database_uri.removeprefix("sqlite:///")
    connection = sqlite3.connect(db_path)
    try:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(productos)").fetchall()
        }
        if columns and "descripcion" not in columns:
            connection.execute(
                "ALTER TABLE productos ADD COLUMN descripcion TEXT NOT NULL DEFAULT ''"
            )
            connection.commit()
    finally:
        connection.close()
