import csv
import json

from sqlalchemy.exc import IntegrityError

from .bd import CSV_FILE, JSON_FILE, TXT_FILE, db
from .productos import Producto


class Inventario:
    def all(self) -> list[Producto]:
        return Producto.query.order_by(Producto.id.asc()).all()

    def get(self, producto_id: int) -> Producto | None:
        return db.session.get(Producto, producto_id)

    def add(self, nombre: str, cantidad: int, precio: float, descripcion: str) -> Producto:
        producto = Producto(
            nombre=nombre,
            cantidad=cantidad,
            precio=precio,
            descripcion=descripcion,
        )
        db.session.add(producto)
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ValueError("Ya existe un producto con ese nombre.") from exc
        self.sync_files()
        return producto

    def update(self, producto_id: int, **campos) -> Producto | None:
        producto = self.get(producto_id)
        if not producto:
            return None

        for campo, valor in campos.items():
            setattr(producto, campo, valor)

        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ValueError("No se pudo actualizar porque el nombre ya existe.") from exc
        self.sync_files()
        return producto

    def delete(self, producto_id: int) -> None:
        producto = self.get(producto_id)
        if not producto:
            return

        db.session.delete(producto)
        db.session.commit()
        self.sync_files()

    def sync_files(self) -> None:
        productos = [producto.to_dict() for producto in self.all()]
        self._write_txt(productos)
        self._write_json(productos)
        self._write_csv(productos)

    def _write_txt(self, productos: list[dict]) -> None:
        with open(TXT_FILE, "w", encoding="utf-8") as txt_file:
            if not productos:
                txt_file.write("No hay productos registrados.\n")
                return

            for producto in productos:
                txt_file.write(
                    f"ID: {producto['id']} | "
                    f"Nombre: {producto['nombre']} | "
                    f"Cantidad: {producto['cantidad']} | "
                    f"Precio: {producto['precio']:.2f} | "
                    f"Descripcion: {producto['descripcion']}\n"
                )

    def _write_json(self, productos: list[dict]) -> None:
        with open(JSON_FILE, "w", encoding="utf-8") as json_file:
            json.dump(productos, json_file, ensure_ascii=False, indent=2)

    def _write_csv(self, productos: list[dict]) -> None:
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as csv_file:
            fieldnames = ["id", "nombre", "cantidad", "precio", "descripcion"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(productos)

    def read_txt(self) -> list[str]:
        with open(TXT_FILE, "r", encoding="utf-8") as txt_file:
            return [line.strip() for line in txt_file.readlines() if line.strip()]

    def read_json(self) -> list[dict]:
        with open(JSON_FILE, "r", encoding="utf-8") as json_file:
            contenido = json_file.read().strip()
            return json.loads(contenido) if contenido else []

    def read_csv(self) -> list[dict]:
        with open(CSV_FILE, "r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader)
