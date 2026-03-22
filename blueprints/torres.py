from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

from Conexión import (
    close_active_cycle,
    fetch_active_cycle_by_torre,
    fetch_cultivos,
    fetch_cycles_by_torre,
    fetch_latest_sensor_reading_by_torre,
    fetch_torre,
    fetch_torres_by_user,
    register_torre,
    start_cultivo_cycle,
)
from form import CicloCultivoFormData, TorreFormData

from .shared import current_torre, current_user_id, login_required, tower_required

torres_bp = Blueprint("torres", __name__)


@torres_bp.route("/torres")
@login_required
def torres():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torres_usuario = fetch_torres_by_user(user_id)
    except Error as exc:
        flash(f"No se pudieron consultar tus torres: {exc}", "error")
        torres_usuario = []

    return render_template("torres.html", torres=torres_usuario)


@torres_bp.route("/torres/registrar", methods=("GET", "POST"))
@login_required
def registrar_torre():
    form_data = TorreFormData()
    if request.method == "POST":
        user_id = current_user_id()
        form_data = TorreFormData.from_request(request.form)
        if form_data.is_valid() and user_id is not None:
            try:
                torre_id = register_torre(
                    codigo_unico=form_data.codigo_unico,
                    nombre=form_data.nombre,
                    ubicacion=form_data.ubicacion,
                    usuario_id=user_id,
                )
                session["torre_id"] = torre_id
                flash("La torre quedó registrada y seleccionada para tu cuenta.", "success")
                return redirect(url_for("torres.elegir_cultivo_actual"))
            except ValueError as exc:
                flash(str(exc), "error")
            except Error as exc:
                flash(f"No se pudo registrar la torre: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "torre_form.html",
        titulo="Registrar torre hidropónica",
        accion="Guardar torre",
        torre=form_data,
        errores=form_data.errors,
    )


@torres_bp.route("/torres/seleccionar/<int:torre_id>")
@login_required
def seleccionar_torre(torre_id):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torre = fetch_torre(torre_id)
    except Error as exc:
        flash(f"No se pudo consultar la torre: {exc}", "error")
        return redirect(url_for("torres.torres"))

    if not torre or torre["usuario_id"] != user_id:
        flash("La torre solicitada no pertenece a tu cuenta.", "error")
        return redirect(url_for("torres.torres"))

    session["torre_id"] = torre_id
    flash(f"Torre activa: {torre['nombre']}.", "success")
    return redirect(url_for("torres.dashboard"))


@torres_bp.route("/torres/cultivo", methods=("GET", "POST"))
@login_required
@tower_required
def elegir_cultivo_actual():
    torre = current_torre()
    if torre is None:
        return redirect(url_for("torres.torres"))

    try:
        catalogo = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo cargar la configuración de cultivo: {exc}", "error")
        return redirect(url_for("torres.dashboard"))

    form_data = CicloCultivoFormData.from_mysql_ciclo(ciclo_activo) if ciclo_activo else CicloCultivoFormData()

    if request.method == "POST":
        form_data = CicloCultivoFormData.from_request(request.form)
        if form_data.is_valid() and form_data.cultivo_id is not None:
            try:
                start_cultivo_cycle(
                    torre_id=torre["id_torre"],
                    cultivo_id=form_data.cultivo_id,
                    fase=form_data.fase,
                    notas=form_data.notas,
                )
                flash("La fase de cultivo de esta torre fue actualizada.", "success")
                return redirect(url_for("torres.dashboard"))
            except Error as exc:
                flash(f"No se pudo actualizar la fase de cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "ciclo_form.html",
        titulo="Elegir cultivo para hoy",
        accion="Guardar fase",
        ciclo=form_data,
        errores=form_data.errors,
        cultivos=catalogo,
        ciclo_activo=ciclo_activo,
        historial_ciclos=historial_ciclos,
        torre=torre,
    )


@torres_bp.route("/torres/cultivo/finalizar", methods=("POST",))
@login_required
@tower_required
def finalizar_ciclo_torre():
    torre = current_torre()
    if torre is None:
        return redirect(url_for("torres.torres"))

    try:
        close_active_cycle(torre["id_torre"])
        flash("La fase activa de la torre fue finalizada.", "success")
    except Error as exc:
        flash(f"No se pudo finalizar la fase activa: {exc}", "error")
    return redirect(url_for("torres.elegir_cultivo_actual"))


@torres_bp.route("/dashboard")
@login_required
@tower_required
def dashboard():
    torre = current_torre()
    if torre is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo cargar el dashboard: {exc}", "error")
        cultivos = []
        ciclo_activo = None
        ultima_lectura = None

    return render_template(
        "dashboard.html",
        cultivos=cultivos,
        ciclo_activo=ciclo_activo,
        torre=torre,
        ultima_lectura=ultima_lectura,
    )
