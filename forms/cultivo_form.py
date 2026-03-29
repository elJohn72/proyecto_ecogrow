try:
    from form import CultivoFormData
except ModuleNotFoundError:
    from ..form import CultivoFormData

__all__ = ["CultivoFormData"]
