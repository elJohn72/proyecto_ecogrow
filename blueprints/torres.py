from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

try:
    from Conexión import (
        close_active_cycle,
        fetch_archived_torres_by_user,
        fetch_active_cycle_by_torre,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_torre,
        fetch_torres_by_user,
        register_torre,
        start_cultivo_cycle,
        update_torre_estado,
    )
    from forms import CicloCultivoFormData, TorreFormData
    from services import fetch_cultivo, fetch_cultivos
except ModuleNotFoundError:
    from ..Conexión import (
        close_active_cycle,
        fetch_archived_torres_by_user,
        fetch_active_cycle_by_torre,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_torre,
        fetch_torres_by_user,
        register_torre,
        start_cultivo_cycle,
        update_torre_estado,
    )
    from ..forms import CicloCultivoFormData, TorreFormData
    from ..services import fetch_cultivo, fetch_cultivos

from .shared import admin_required, current_torre, current_user_id, login_required, tower_required

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


@torres_bp.route("/torres/inactivas")
@login_required
@admin_required
def torres_inactivas():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torres_usuario = fetch_archived_torres_by_user(user_id)
    except Error as exc:
        flash(f"No se pudieron consultar tus torres inactivas: {exc}", "error")
        torres_usuario = []

    return render_template("torres_inactivas.html", torres=torres_usuario)


@torres_bp.route("/torres/registrar", methods=("GET", "POST"))
@login_required
@admin_required
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

    if str(torre.get("estado", "")).lower() == "inactivo":
        flash("No puedes seleccionar una torre inactiva. Actívala primero.", "error")
        return redirect(url_for("torres.torres_inactivas"))

    session["torre_id"] = torre_id
    flash(f"Torre activa: {torre['nombre']}.", "success")
    return redirect(url_for("torres.dashboard"))


@torres_bp.route("/torres/cultivo", methods=("GET", "POST"))
@login_required
@tower_required
@admin_required
def elegir_cultivo_actual():
    user_id = current_user_id()
    torre = current_torre()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        catalogo = fetch_cultivos(user_id)
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
                if not fetch_cultivo(form_data.cultivo_id, user_id):
                    flash("Solo puedes asignar cultivos registrados en tu cuenta.", "error")
                    return redirect(url_for("torres.elegir_cultivo_actual"))
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
@admin_required
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


@torres_bp.route("/torres/inactivar/<int:torre_id>", methods=("POST",))
@login_required
@admin_required
def inactivar_torre(torre_id):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torre = fetch_torre(torre_id)
        if not torre or torre["usuario_id"] != user_id:
            flash("La torre solicitada no pertenece a tu cuenta.", "error")
            return redirect(url_for("torres.torres"))

        update_torre_estado(torre_id, "inactivo")
        if session.get("torre_id") == torre_id:
            session.pop("torre_id", None)
        flash("Torre inactivada correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo inactivar la torre: {exc}", "error")
    return redirect(url_for("torres.torres"))


@torres_bp.route("/torres/activar/<int:torre_id>", methods=("POST",))
@login_required
@admin_required
def activar_torre(torre_id):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torre = fetch_torre(torre_id)
        if not torre or torre["usuario_id"] != user_id:
            flash("La torre solicitada no pertenece a tu cuenta.", "error")
            return redirect(url_for("torres.torres_inactivas"))

        update_torre_estado(torre_id, "registrada")
        flash("Torre activada correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo activar la torre: {exc}", "error")
    return redirect(url_for("torres.torres_inactivas"))


@torres_bp.route("/dashboard")
@login_required
@tower_required
def dashboard():
    user_id = current_user_id()
    torre = current_torre()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos = fetch_cultivos(user_id)
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
