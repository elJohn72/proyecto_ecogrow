try:
    from form import CicloCultivoFormData, TorreFormData
except ModuleNotFoundError:
    from ..form import CicloCultivoFormData, TorreFormData

__all__ = ["CicloCultivoFormData", "TorreFormData"]
