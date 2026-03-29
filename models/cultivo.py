from dataclasses import dataclass


@dataclass
class Cultivo:
    id_cultivo: int
    nombre: str
    variedad: str
    ubicacion: str
    estado: str
    descripcion: str

    @classmethod
    def from_mysql_row(cls, row: dict):
        return cls(
            id_cultivo=int(row["id_cultivo"]),
            nombre=str(row["nombre"]),
            variedad=str(row["variedad"]),
            ubicacion=str(row["ubicacion"]),
            estado=str(row["estado"]),
            descripcion=str(row["descripcion"]),
        )
