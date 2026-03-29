try:
    from form import LoginFormData
except ModuleNotFoundError:
    from ..form import LoginFormData

__all__ = ["LoginFormData"]
