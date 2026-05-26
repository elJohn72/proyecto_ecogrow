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
    torre_id: int | None = None
    nombre: str = ""
    variedad: str = ""
    ubicacion: str = ""
    estado: str = ""
    descripcion: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "CultivoFormData":
        errors: list[str] = []
        torre_raw = form.get("torre_id", "").strip()
        nombre = form.get("nombre", "").strip()
        variedad = form.get("variedad", "").strip()
        ubicacion = form.get("ubicacion", "").strip()
        estado = form.get("estado", "").strip()
        descripcion = form.get("descripcion", "").strip()

        torre_id = None
        try:
            torre_id = int(torre_raw)
            if torre_id <= 0:
                errors.append("Selecciona una torre valida.")
        except ValueError:
            errors.append("Selecciona una torre valida.")

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
            torre_id=torre_id,
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
            torre_id=cultivo.get("torre_id"),
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


@dataclass
class CosechaFormData:
    peso_kg: float | None = None
    plantas_cosechadas: int | None = None
    notas: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "CosechaFormData":
        errors: list[str] = []
        peso_raw = form.get("peso_kg", "").strip()
        plantas_raw = form.get("plantas_cosechadas", "").strip()
        notas = form.get("notas", "").strip()

        peso_kg = None
        if not peso_raw:
            errors.append("Indica el peso total cosechado en kg.")
        else:
            try:
                peso_kg = float(peso_raw.replace(",", "."))
                if peso_kg <= 0:
                    errors.append("El peso debe ser mayor que cero.")
            except ValueError:
                errors.append("El peso en kg no es valido.")

        plantas_cosechadas = None
        if plantas_raw:
            try:
                plantas_cosechadas = int(plantas_raw)
                if plantas_cosechadas <= 0:
                    errors.append("El numero de plantas debe ser mayor que cero.")
            except ValueError:
                errors.append("El numero de plantas no es valido.")

        return cls(peso_kg=peso_kg, plantas_cosechadas=plantas_cosechadas, notas=notas, errors=errors)

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class TorreControlFormData:
    module_size_mm: int = 80
    deposito_litros: float = 5.0
    bomba_modelo: str = ""
    head_height_m: float = 1.4
    ph_min: float = 5.5
    ph_max: float = 6.5
    ec_min: float = 1.4
    ec_max: float = 2.4
    temperatura_agua_min: float = 18.0
    temperatura_agua_max: float = 24.0
    nivel_minimo: float = 20.0
    nivel_objetivo: float = 85.0
    irrigation_on_minutes: int = 15
    irrigation_off_minutes: int = 60
    riego_habilitado: bool = True
    estrategia_riego: str = "oxigenacion_radicular"
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "TorreControlFormData":
        errors: list[str] = []

        def _float_field(name: str, label: str) -> float:
            raw = form.get(name, "").strip().replace(",", ".")
            try:
                return float(raw)
            except ValueError as exc:
                raise ValueError(f"{label} no es valido.") from exc

        def _int_field(name: str, label: str) -> int:
            raw = form.get(name, "").strip()
            try:
                return int(raw)
            except ValueError as exc:
                raise ValueError(f"{label} no es valido.") from exc

        try:
            data = cls(
                module_size_mm=_int_field("module_size_mm", "Tamano de modulo"),
                deposito_litros=_float_field("deposito_litros", "Deposito"),
                bomba_modelo=form.get("bomba_modelo", "").strip(),
                head_height_m=_float_field("head_height_m", "Altura de bombeo"),
                ph_min=_float_field("ph_min", "pH minimo"),
                ph_max=_float_field("ph_max", "pH maximo"),
                ec_min=_float_field("ec_min", "EC minima"),
                ec_max=_float_field("ec_max", "EC maxima"),
                temperatura_agua_min=_float_field("temperatura_agua_min", "Temperatura minima"),
                temperatura_agua_max=_float_field("temperatura_agua_max", "Temperatura maxima"),
                nivel_minimo=_float_field("nivel_minimo", "Nivel minimo"),
                nivel_objetivo=_float_field("nivel_objetivo", "Nivel objetivo"),
                irrigation_on_minutes=_int_field("irrigation_on_minutes", "Minutos ON"),
                irrigation_off_minutes=_int_field("irrigation_off_minutes", "Minutos OFF"),
                riego_habilitado=form.get("riego_habilitado") == "on",
                estrategia_riego=form.get("estrategia_riego", "oxigenacion_radicular").strip(),
            )
        except ValueError as exc:
            errors.append(str(exc))
            return cls(errors=errors)

        if not data.bomba_modelo:
            errors.append("Indica el modelo de bomba.")
        if data.ph_min >= data.ph_max:
            errors.append("El pH minimo debe ser menor que el maximo.")
        if data.ec_min >= data.ec_max:
            errors.append("La EC minima debe ser menor que la maxima.")
        if data.temperatura_agua_min >= data.temperatura_agua_max:
            errors.append("La temperatura minima del agua debe ser menor que la maxima.")
        if data.nivel_minimo >= data.nivel_objetivo:
            errors.append("El nivel minimo debe ser menor que el objetivo.")
        if data.irrigation_on_minutes <= 0 or data.irrigation_off_minutes <= 0:
            errors.append("Los minutos de riego deben ser mayores que cero.")

        data.errors = errors
        return data

    @classmethod
    def from_mysql(cls, config: dict, programacion: dict | None) -> "TorreControlFormData":
        programacion = programacion or {}
        return cls(
            module_size_mm=int(config.get("module_size_mm", 80)),
            deposito_litros=float(config.get("deposito_litros", 5)),
            bomba_modelo=str(config.get("bomba_modelo", "")),
            head_height_m=float(config.get("head_height_m", 1.4)),
            ph_min=float(config.get("ph_min", 5.5)),
            ph_max=float(config.get("ph_max", 6.5)),
            ec_min=float(config.get("ec_min", 1.4)),
            ec_max=float(config.get("ec_max", 2.4)),
            temperatura_agua_min=float(config.get("temperatura_agua_min", 18)),
            temperatura_agua_max=float(config.get("temperatura_agua_max", 24)),
            nivel_minimo=float(config.get("nivel_minimo", 20)),
            nivel_objetivo=float(config.get("nivel_objetivo", 85)),
            irrigation_on_minutes=int(
                programacion.get("minutos_encendido", config.get("irrigation_on_minutes", 15))
            ),
            irrigation_off_minutes=int(
                programacion.get("minutos_apagado", config.get("irrigation_off_minutes", 60))
            ),
            riego_habilitado=bool(programacion.get("habilitado", True)),
            estrategia_riego=str(programacion.get("estrategia", "oxigenacion_radicular")),
        )

    def is_valid(self) -> bool:
        return not self.errors
