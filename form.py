from dataclasses import dataclass, field


@dataclass
class UsuarioFormData:
    nombre: str = ""
    mail: str = ""
    password: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form, *, password_required: bool = True) -> "UsuarioFormData":
        errors: list[str] = []
        nombre = form.get("nombre", "").strip()
        mail = form.get("mail", "").strip()
        password = form.get("password", "").strip()

        if not nombre:
            errors.append("El nombre es obligatorio.")
        if not mail:
            errors.append("El correo es obligatorio.")
        elif "@" not in mail or "." not in mail:
            errors.append("El correo no tiene un formato valido.")
        if password_required and not password:
            errors.append("La contrasena es obligatoria.")
        elif password and len(password) < 8:
            errors.append("La contrasena debe tener al menos 8 caracteres.")

        return cls(nombre=nombre, mail=mail, password=password, errors=errors)

    @classmethod
    def from_mysql_usuario(cls, usuario: dict) -> "UsuarioFormData":
        return cls(
            nombre=usuario.get("nombre", ""),
            mail=usuario.get("mail", ""),
        )

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class LoginFormData:
    mail: str = ""
    password: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "LoginFormData":
        errors: list[str] = []
        mail = form.get("mail", "").strip()
        password = form.get("password", "").strip()

        if not mail:
            errors.append("El correo es obligatorio.")
        if not password:
            errors.append("La contrasena es obligatoria.")

        return cls(mail=mail, password=password, errors=errors)

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class CultivoFormData:
    nombre: str = ""
    variedad: str = ""
    ubicacion: str = ""
    estado: str = ""
    descripcion: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "CultivoFormData":
        errors: list[str] = []
        nombre = form.get("nombre", "").strip()
        variedad = form.get("variedad", "").strip()
        ubicacion = form.get("ubicacion", "").strip()
        estado = form.get("estado", "").strip()
        descripcion = form.get("descripcion", "").strip()

        if not nombre:
            errors.append("El nombre del cultivo es obligatorio.")
        if not variedad:
            errors.append("La variedad es obligatoria.")
        if not ubicacion:
            errors.append("La ubicacion es obligatoria.")
        if not estado:
            errors.append("El estado es obligatorio.")
        if not descripcion:
            errors.append("La descripcion es obligatoria.")

        return cls(
            nombre=nombre,
            variedad=variedad,
            ubicacion=ubicacion,
            estado=estado,
            descripcion=descripcion,
            errors=errors,
        )

    @classmethod
    def from_mysql_cultivo(cls, cultivo: dict) -> "CultivoFormData":
        return cls(
            nombre=cultivo.get("nombre", ""),
            variedad=cultivo.get("variedad", ""),
            ubicacion=cultivo.get("ubicacion", ""),
            estado=cultivo.get("estado", ""),
            descripcion=cultivo.get("descripcion", ""),
        )

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class TorreFormData:
    codigo_unico: str = ""
    nombre: str = ""
    ubicacion: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "TorreFormData":
        errors: list[str] = []
        codigo_unico = form.get("codigo_unico", "").strip().upper()
        nombre = form.get("nombre", "").strip()
        ubicacion = form.get("ubicacion", "").strip()

        if not codigo_unico:
            errors.append("El codigo unico de la torre es obligatorio.")
        elif len(codigo_unico) < 6:
            errors.append("El codigo unico debe tener al menos 6 caracteres.")

        if not nombre:
            errors.append("El nombre de la torre es obligatorio.")

        if not ubicacion:
            errors.append("La ubicacion de la torre es obligatoria.")

        return cls(
            codigo_unico=codigo_unico,
            nombre=nombre,
            ubicacion=ubicacion,
            errors=errors,
        )

    @classmethod
    def from_mysql_torre(cls, torre: dict) -> "TorreFormData":
        return cls(
            codigo_unico=torre.get("codigo_unico", ""),
            nombre=torre.get("nombre", ""),
            ubicacion=torre.get("ubicacion", ""),
        )

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class CicloCultivoFormData:
    cultivo_id: int | None = None
    fase: str = ""
    notas: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "CicloCultivoFormData":
        errors: list[str] = []
        cultivo_raw = form.get("cultivo_id", "").strip()
        fase = form.get("fase", "").strip()
        notas = form.get("notas", "").strip()

        cultivo_id = None
        try:
            cultivo_id = int(cultivo_raw)
            if cultivo_id <= 0:
                errors.append("Selecciona un cultivo valido.")
        except ValueError:
            errors.append("Selecciona un cultivo valido.")

        if not fase:
            errors.append("La fase actual es obligatoria.")

        return cls(
            cultivo_id=cultivo_id,
            fase=fase,
            notas=notas,
            errors=errors,
        )

    @classmethod
    def from_mysql_ciclo(cls, ciclo: dict) -> "CicloCultivoFormData":
        return cls(
            cultivo_id=ciclo.get("cultivo_id"),
            fase=ciclo.get("fase", ""),
            notas=ciclo.get("notas", ""),
        )

    def is_valid(self) -> bool:
        return not self.errors
