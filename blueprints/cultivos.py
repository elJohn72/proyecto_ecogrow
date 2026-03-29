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
        activate_cultivo,
        create_cultivo,
        delete_cultivo,
        fetch_cultivo,
        fetch_cultivos,
        fetch_inactive_cultivos,
        generate_cultivos_pdf,
        inactivate_cultivo,
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
        activate_cultivo,
        create_cultivo,
        delete_cultivo,
        fetch_cultivo,
        fetch_cultivos,
        fetch_inactive_cultivos,
        generate_cultivos_pdf,
        inactivate_cultivo,
        update_cultivo,
    )

from .shared import admin_required, current_torre, current_user_id, login_required, tower_required

cultivos_bp = Blueprint("cultivos", __name__)


@cultivos_bp.route("/cultivos")
@login_required
@tower_required
def cultivos():
    user_id = current_user_id()
    torre = current_torre()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos_registrados = fetch_cultivos(user_id)
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


@cultivos_bp.route("/cultivos/inactivos")
@login_required
@admin_required
def cultivos_inactivos():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        cultivos_registrados = fetch_inactive_cultivos(user_id)
    except Error as exc:
        flash(f"No se pudieron consultar los cultivos inactivos: {exc}", "error")
        cultivos_registrados = []

    return render_template("cultivos/inactivos.html", cultivos=cultivos_registrados)


@cultivos_bp.route("/cultivos/nuevo", methods=("GET", "POST"))
@login_required
@admin_required
def crear_cultivo():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    form_data = CultivoFormData()
    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                create_cultivo(
                    usuario_id=user_id,
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
@admin_required
def editar_cultivo(cid):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        cultivo = fetch_cultivo(cid, user_id)
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
                    usuario_id=user_id,
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
@admin_required
def borrar_cultivo(cid):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        delete_cultivo(cid, user_id)
        flash("Cultivo eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Error as exc:
        flash(f"No se pudo eliminar el cultivo: {exc}", "error")
    return redirect(url_for("cultivos.cultivos"))


@cultivos_bp.route("/cultivos/inactivar/<int:cid>", methods=("POST",))
@login_required
@admin_required
def inactivar_cultivo(cid):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        inactivate_cultivo(cid, user_id)
        flash("Cultivo inactivado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Error as exc:
        flash(f"No se pudo inactivar el cultivo: {exc}", "error")
    return redirect(url_for("cultivos.cultivos"))


@cultivos_bp.route("/cultivos/activar/<int:cid>", methods=("POST",))
@login_required
@admin_required
def activar_cultivo(cid):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        activate_cultivo(cid, user_id)
        flash("Cultivo activado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except Error as exc:
        flash(f"No se pudo activar el cultivo: {exc}", "error")
    return redirect(url_for("cultivos.cultivos_inactivos"))


@cultivos_bp.route("/cultivos/reporte/pdf")
@login_required
def reporte_cultivos_pdf():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))
    try:
        pdf_bytes = generate_cultivos_pdf(user_id)
    except Error as exc:
        flash(f"No se pudo generar el reporte de cultivos: {exc}", "error")
        return redirect(url_for("cultivos.cultivos"))

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="reporte_cultivos_ecogrow.pdf",
    )
