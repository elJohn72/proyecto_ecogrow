from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from mysql.connector import Error

try:
    from Conexión import (
        fetch_active_cycle_by_torre,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
    )
    from forms import CultivoFormData
    from services import (
        create_cultivo,
        delete_cultivo,
        fetch_cultivo,
        fetch_cultivos,
        generate_cultivos_pdf,
        update_cultivo,
    )
except ModuleNotFoundError:
    from ..Conexión import (
        fetch_active_cycle_by_torre,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
    )
    from ..forms import CultivoFormData
    from ..services import (
        create_cultivo,
        delete_cultivo,
        fetch_cultivo,
        fetch_cultivos,
        generate_cultivos_pdf,
        update_cultivo,
    )

from .shared import current_torre, login_required, tower_required

cultivos_bp = Blueprint("cultivos", __name__)


@cultivos_bp.route("/cultivos")
@login_required
@tower_required
def cultivos():
    torre = current_torre()
    if torre is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos_registrados = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudieron consultar los cultivos: {exc}", "error")
        cultivos_registrados = []
        ciclo_activo = None
        historial_ciclos = []
        ultima_lectura = None

    return render_template(
        "cultivos/lista.html",
        cultivos=cultivos_registrados,
        ciclo_activo=ciclo_activo,
        historial_ciclos=historial_ciclos,
        torre=torre,
        ultima_lectura=ultima_lectura,
    )


@cultivos_bp.route("/cultivos/nuevo", methods=("GET", "POST"))
@login_required
def crear_cultivo():
    form_data = CultivoFormData()
    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                create_cultivo(
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                flash("Cultivo registrado correctamente.", "success")
                return redirect(url_for("cultivos.cultivos"))
            except Error as exc:
                flash(f"No se pudo guardar el cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "cultivos/form.html",
        titulo="Nuevo cultivo",
        accion="Guardar cultivo",
        cultivo=form_data,
        errores=form_data.errors,
    )


@cultivos_bp.route("/cultivos/editar/<int:cid>", methods=("GET", "POST"))
@login_required
def editar_cultivo(cid):
    try:
        cultivo = fetch_cultivo(cid)
    except Error as exc:
        flash(f"No se pudo consultar el cultivo: {exc}", "error")
        return redirect(url_for("cultivos.cultivos"))

    if not cultivo:
        flash("Cultivo no encontrado.", "error")
        return redirect(url_for("cultivos.cultivos"))

    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                update_cultivo(
                    cid,
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                flash("Cultivo actualizado correctamente.", "success")
                return redirect(url_for("cultivos.cultivos"))
            except Error as exc:
                flash(f"No se pudo actualizar el cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = CultivoFormData.from_mysql_cultivo(
            {
                "nombre": cultivo.nombre,
                "variedad": cultivo.variedad,
                "ubicacion": cultivo.ubicacion,
                "estado": cultivo.estado,
                "descripcion": cultivo.descripcion,
            }
        )

    return render_template(
        "cultivos/form.html",
        titulo="Editar cultivo",
        accion="Actualizar cultivo",
        cultivo=form_data,
        errores=form_data.errors,
    )


@cultivos_bp.route("/cultivos/borrar/<int:cid>", methods=("POST",))
@login_required
def borrar_cultivo(cid):
    try:
        delete_cultivo(cid)
        flash("Cultivo eliminado correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el cultivo: {exc}", "error")
    return redirect(url_for("cultivos.cultivos"))


@cultivos_bp.route("/cultivos/reporte/pdf")
@login_required
def reporte_cultivos_pdf():
    try:
        pdf_bytes = generate_cultivos_pdf()
    except Error as exc:
        flash(f"No se pudo generar el reporte de cultivos: {exc}", "error")
        return redirect(url_for("cultivos.cultivos"))

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="reporte_cultivos_ecogrow.pdf",
    )
