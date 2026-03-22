from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, user_id: int, nombre: str, mail: str, password: str = ""):
        self.id = str(user_id)
        self.nombre = nombre
        self.mail = mail
        self.password = password

    @classmethod
    def from_mysql_row(cls, row: dict | None):
        if not row:
            return None
        return cls(
            user_id=row["id_usuario"],
            nombre=row.get("nombre", ""),
            mail=row.get("mail", ""),
            password=row.get("password", ""),
        )
