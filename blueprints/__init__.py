from .auth import auth_bp
from .cultivos import cultivos_bp
from .inventario import inventario_bp
from .main import main_bp
from .mysql import mysql_bp
from .sensores import sensores_bp
from .torres import torres_bp

__all__ = [
    "auth_bp",
    "cultivos_bp",
    "inventario_bp",
    "main_bp",
    "mysql_bp",
    "sensores_bp",
    "torres_bp",
]
