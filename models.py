import sqlite3
from typing import Optional, List

DB = "inventario.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL
    )
    """
    )
    conn.commit()
    conn.close()


class Producto:
    def __init__(self, nombre: str, cantidad: int, precio: float, id: Optional[int] = None):
        self.id = id
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio

    def save(self):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        if self.id is None:
            cur.execute(
                "INSERT INTO productos (nombre,cantidad,precio) VALUES (?,?,?)",
                (self.nombre, self.cantidad, self.precio),
            )
            self.id = cur.lastrowid
        else:
            cur.execute(
                "UPDATE productos SET nombre=?, cantidad=?, precio=? WHERE id=?",
                (self.nombre, self.cantidad, self.precio, self.id),
            )
        conn.commit()
        conn.close()

    @staticmethod
    def delete_by_id(prod_id: int):
        conn = sqlite3.connect(DB)
        conn.execute("DELETE FROM productos WHERE id=?", (prod_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def all() -> List['Producto']:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT id,nombre,cantidad,precio FROM productos")
        rows = cur.fetchall()
        conn.close()
        return [Producto(id=r[0], nombre=r[1], cantidad=r[2], precio=r[3]) for r in rows]


class Inventario:
    def __init__(self):
        self.productos: dict[int, Producto] = {}
        self._load()

    def _load(self):
        for p in Producto.all():
            self.productos[p.id] = p

    def add(self, producto: Producto):
        producto.save()
        self.productos[producto.id] = producto

    def delete(self, prod_id: int):
        if prod_id in self.productos:
            Producto.delete_by_id(prod_id)
            del self.productos[prod_id]

    def update(self, prod_id: int, **campos):
        prod = self.productos.get(prod_id)
        if not prod:
            return None
        for k, v in campos.items():
            setattr(prod, k, v)
        prod.save()
        return prod

    def search(self, nombre: str):
        return [p for p in self.productos.values() if nombre.lower() in p.nombre.lower()]

    def all(self):
        return list(self.productos.values())
