from datetime import datetime

try:
    from conexion.conexion import (
        count_cycles_by_cultivo,
        delete_cultivo as delete_cultivo_db,
        fetch_archived_cultivos as fetch_archived_cultivos_db,
        fetch_cultivo as fetch_cultivo_db,
        fetch_cultivos as fetch_cultivos_db,
        insert_cultivo,
        update_cultivo as update_cultivo_db,
        update_cultivo_estado as update_cultivo_estado_db,
    )
    from models import Cultivo
except ModuleNotFoundError:
    from ..conexion.conexion import (
        count_cycles_by_cultivo,
        delete_cultivo as delete_cultivo_db,
        fetch_archived_cultivos as fetch_archived_cultivos_db,
        fetch_cultivo as fetch_cultivo_db,
        fetch_cultivos as fetch_cultivos_db,
        insert_cultivo,
        update_cultivo as update_cultivo_db,
        update_cultivo_estado as update_cultivo_estado_db,
    )
    from ..models import Cultivo


def fetch_cultivos(usuario_id: int) -> list[Cultivo]:
    return [Cultivo.from_mysql_row(row) for row in fetch_cultivos_db(usuario_id)]


def fetch_inactive_cultivos(usuario_id: int) -> list[Cultivo]:
    return [Cultivo.from_mysql_row(row) for row in fetch_archived_cultivos_db(usuario_id)]


def fetch_cultivo(cultivo_id: int, usuario_id: int) -> Cultivo | None:
    row = fetch_cultivo_db(cultivo_id, usuario_id)
    return Cultivo.from_mysql_row(row) if row else None


def create_cultivo(usuario_id: int, torre_id: int, nombre: str, variedad: str, ubicacion: str, estado: str, descripcion: str) -> int:
    return insert_cultivo(usuario_id=usuario_id, torre_id=torre_id, nombre=nombre, variedad=variedad, ubicacion=ubicacion, estado=estado, descripcion=descripcion)


def update_cultivo(cultivo_id: int, usuario_id: int, torre_id: int, nombre: str, variedad: str, ubicacion: str, estado: str, descripcion: str) -> None:
    update_cultivo_db(cultivo_id, usuario_id=usuario_id, torre_id=torre_id, nombre=nombre, variedad=variedad, ubicacion=ubicacion, estado=estado, descripcion=descripcion)


def delete_cultivo(cultivo_id: int, usuario_id: int) -> None:
    if count_cycles_by_cultivo(cultivo_id, usuario_id) > 0:
        raise ValueError("No se puede eliminar este cultivo porque ya tiene ciclos de cultivo asociados.")
    delete_cultivo_db(cultivo_id, usuario_id)


def inactivate_cultivo(cultivo_id: int, usuario_id: int) -> None:
    if count_cycles_by_cultivo(cultivo_id, usuario_id) == 0:
        raise ValueError("Solo se pueden inactivar cultivos que ya tienen historial asociado.")
    update_cultivo_estado_db(cultivo_id, usuario_id, "inactivo")


def activate_cultivo(cultivo_id: int, usuario_id: int) -> None:
    update_cultivo_estado_db(cultivo_id, usuario_id, "activo")


def generate_cultivos_pdf(usuario_id: int) -> bytes:
    from fpdf import FPDF

    cultivos = fetch_cultivos(usuario_id)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Reporte de cultivos EcoGrow", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    headers = (("ID", 12), ("Nombre", 34), ("Variedad", 34), ("Ubicacion", 40), ("Estado", 25), ("Descripcion", 45))
    pdf.set_font("Helvetica", "B", 9)
    for label, width in headers:
        pdf.cell(width, 8, label, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=8)
    if not cultivos:
        pdf.cell(0, 8, "No hay cultivos registrados.", border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        for cultivo in cultivos:
            row = (
                str(cultivo.id_cultivo),
                cultivo.nombre[:18],
                cultivo.variedad[:18],
                cultivo.ubicacion[:22],
                cultivo.estado[:12],
                cultivo.descripcion[:26],
            )
            for (_, width), value in zip(headers, row):
                pdf.cell(width, 8, value, border=1)
            pdf.ln()

    return bytes(pdf.output())
