try:
    from form import UsuarioFormData
except ModuleNotFoundError:
    from ..form import UsuarioFormData

__all__ = ["UsuarioFormData"]
