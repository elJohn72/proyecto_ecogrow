from dataclasses import dataclass, field


@dataclass
class ProductoFormData:
    nombre: str = ""
    cantidad: int | None = None
    precio: float | None = None
    descripcion: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "ProductoFormData":
        errors: list[str] = []
        nombre = form.get("nombre", "").strip()
        descripcion = form.get("descripcion", "").strip()

        cantidad_raw = form.get("cantidad", "").strip()
        precio_raw = form.get("precio", "").strip()

        cantidad = None
        precio = None

        if not nombre:
            errors.append("El nombre es obligatorio.")
        if not descripcion:
            errors.append("La descripcion es obligatoria.")

        try:
            cantidad = int(cantidad_raw)
            if cantidad < 0:
                errors.append("La cantidad no puede ser negativa.")
        except ValueError:
            errors.append("La cantidad debe ser un numero entero.")

        try:
            precio = float(precio_raw)
            if precio < 0:
                errors.append("El precio no puede ser negativo.")
        except ValueError:
            errors.append("El precio debe ser un numero valido.")

        return cls(
            nombre=nombre,
            cantidad=cantidad,
            precio=precio,
            descripcion=descripcion,
            errors=errors,
        )

    @classmethod
    def from_producto(cls, producto) -> "ProductoFormData":
        return cls(
            nombre=producto.nombre,
            cantidad=producto.cantidad,
            precio=producto.precio,
            descripcion=producto.descripcion,
        )

    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class UsuarioFormData:
    nombre: str = ""
    mail: str = ""
    password: str = ""
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, form) -> "UsuarioFormData":
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
        if not password:
            errors.append("La contrasena es obligatoria.")

        return cls(nombre=nombre, mail=mail, password=password, errors=errors)

    @classmethod
    def from_mysql_usuario(cls, usuario: dict) -> "UsuarioFormData":
        return cls(
            nombre=usuario.get("nombre", ""),
            mail=usuario.get("mail", ""),
            password=usuario.get("password", ""),
        )

    def is_valid(self) -> bool:
        return not self.errors
