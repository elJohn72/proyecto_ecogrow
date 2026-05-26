from dataclasses import dataclass


@dataclass
class Cultivo:
    id_cultivo: int
    usuario_id: int | None
    torre_id: int | None
    nombre: str
    variedad: str
    ubicacion: str
    estado: str
    descripcion: str
    torre_nombre: str = ""
    total_ciclos: int = 0

    @property
    def can_delete(self) -> bool:
        return self.total_ciclos == 0

    @classmethod
    def from_mysql_row(cls, row: dict):
        return cls(
            id_cultivo=int(row["id_cultivo"]),
            usuario_id=int(row["usuario_id"]) if row.get("usuario_id") is not None else None,
            torre_id=int(row["torre_id"]) if row.get("torre_id") is not None else None,
            torre_nombre=str(row.get("torre_nombre") or ""),
            nombre=str(row["nombre"]),
            variedad=str(row["variedad"]),
            ubicacion=str(row["ubicacion"]),
            estado=str(row["estado"]),
            descripcion=str(row["descripcion"]),
            total_ciclos=int(row.get("total_ciclos", 0) or 0),
        )
