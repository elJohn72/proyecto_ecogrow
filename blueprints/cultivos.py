from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from mysql.connector import Error

try:
    from Conexión import (
        fetch_active_cycle_by_torre,
        fetch_cycles_by_torre,
        fetch_torre,
        fetch_torres_by_user,
        fetch_latest_sensor_reading_by_torre,
        fetch_cultivo_phase_options,
        start_cultivo_cycle,
        sync_cultivo_phase_options,
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
        fetch_torre,
        fetch_torres_by_user,
        fetch_latest_sensor_reading_by_torre,
        fetch_cultivo_phase_options,
        start_cultivo_cycle,
        sync_cultivo_phase_options,
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

from .shared import current_torre, current_user_id, login_required

cultivos_bp = Blueprint("cultivos", __name__)

CULTIVO_OPTIONS = {
    "Lechuga": {
        "variedades": [
            "Salanova Verde",
            "Salanova Roja",
            "Hoja de Roble",
            "Little Gem",
            "Lollo Rossa",
            "Lollo Bionda",
            "Kristin",
        ],
        "fases": {
            "Salanova Verde": ["germinacion", "plantula", "formacion de bola", "cosecha"],
            "Salanova Roja": ["germinacion", "plantula", "formacion de bola", "cosecha"],
            "Hoja de Roble": ["germinacion", "plantula", "desarrollo foliar", "cosecha continua"],
            "Little Gem": ["germinacion", "plantula", "formacion de cogollo", "cosecha"],
            "Lollo Rossa": ["germinacion", "plantula", "desarrollo foliar", "cosecha"],
            "Lollo Bionda": ["germinacion", "plantula", "desarrollo foliar", "cosecha"],
            "Kristin": ["germinacion", "plantula", "desarrollo resistente", "cosecha"],
        },
    },
    "Acelga": {
        "variedades": ["Fordhook Giant", "Bright Lights"],
        "fases": {
            "Fordhook Giant": ["germinacion", "plantula", "desarrollo foliar", "cosecha continua"],
            "Bright Lights": ["germinacion", "plantula", "desarrollo foliar", "cosecha continua"],
        },
    },
    "Espinaca": {
        "variedades": ["Baby Leaf", "Viroflay"],
        "fases": {
            "Baby Leaf": ["germinacion", "plantula", "desarrollo foliar", "cosecha"],
            "Viroflay": ["germinacion", "plantula", "desarrollo foliar", "cosecha"],
        },
    },
    "Rucula": {
        "variedades": ["Cultivada", "Silvestre"],
        "fases": {
            "Cultivada": ["germinacion", "plantula", "desarrollo foliar", "cosecha continua"],
            "Silvestre": ["germinacion", "plantula", "desarrollo foliar", "cosecha continua"],
        },
    },
    "Albahaca": {
        "variedades": ["Genovesa", "Morada"],
        "fases": {
            "Genovesa": ["germinacion", "plantula", "ramificacion", "cosecha continua"],
            "Morada": ["germinacion", "plantula", "ramificacion", "cosecha continua"],
        },
    },
}


def _variety_options_for_name(nombre: str | None = None) -> list[str]:
    if not nombre:
        return []
    return list(CULTIVO_OPTIONS.get(nombre, {}).get("variedades", []))


def _phase_options_for_form(nombre: str | None = None, variedad: str | None = None) -> list[str]:
    default_phases = ["germinacion", "plantula", "desarrollo foliar", "cosecha"]
    if not nombre or not variedad:
        return default_phases
    fases = CULTIVO_OPTIONS.get(nombre, {}).get("fases", {}).get(variedad)
    return list(fases or default_phases)


def _build_variety_options_by_name() -> dict[str, list[str]]:
    return {
        nombre: list(config["variedades"])
        for nombre, config in CULTIVO_OPTIONS.items()
    }


def _build_phase_options_by_variety() -> dict[str, list[str]]:
    phase_options: dict[str, list[str]] = {}
    for config in CULTIVO_OPTIONS.values():
        for variedad, fases in config["fases"].items():
            phase_options[variedad] = list(fases)
    return phase_options


@cultivos_bp.route("/cultivos")
@login_required
def cultivos():
    user_id = current_user_id()
    torre = current_torre()
    if user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos_registrados = fetch_cultivos(user_id)
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"]) if torre else None
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"]) if torre else []
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"]) if torre else None
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
def crear_cultivo():
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        torres = fetch_torres_by_user(user_id)
    except Error as exc:
        flash(f"No se pudieron cargar tus torres: {exc}", "error")
        return redirect(url_for("torres.torres"))

    if not torres:
        flash("Primero registra al menos una torre para vincular el cultivo.", "error")
        return redirect(url_for("torres.torres"))

    form_data = CultivoFormData()
    phase_options_by_variety = _build_phase_options_by_variety()
    variety_options_by_name = _build_variety_options_by_name()
    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        allowed_phases = _phase_options_for_form(form_data.nombre, form_data.variedad)
        if form_data.nombre not in CULTIVO_OPTIONS:
            form_data.errors.append("Selecciona un tipo de cultivo valido.")
        if form_data.variedad not in _variety_options_for_name(form_data.nombre):
            form_data.errors.append("Selecciona una variedad valida para el cultivo elegido.")
        if form_data.estado.lower() not in allowed_phases:
            form_data.errors.append("Selecciona una etapa valida para la variedad elegida.")
        torre = next((item for item in torres if item["id_torre"] == form_data.torre_id), None)
        if torre is None:
            form_data.errors.append("Selecciona una torre valida para este cultivo.")

        if form_data.is_valid():
            try:
                cultivo_id = create_cultivo(
                    usuario_id=user_id,
                    torre_id=form_data.torre_id,
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                sync_cultivo_phase_options(cultivo_id, form_data.variedad)
                start_cultivo_cycle(
                    torre_id=form_data.torre_id,
                    cultivo_id=cultivo_id,
                    fase=form_data.estado,
                    notas=form_data.descripcion,
                )
                flash(f"Cultivo registrado y vinculado a la torre {torre['nombre'] }.", "success")
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
        torres=torres,
        nombre_options=list(CULTIVO_OPTIONS.keys()),
        variedad_options_by_nombre=variety_options_by_name,
        phase_options_by_variety=phase_options_by_variety,
    )


@cultivos_bp.route("/cultivos/editar/<int:cid>", methods=("GET", "POST"))
@login_required
def editar_cultivo(cid):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torres = fetch_torres_by_user(user_id)
    except Error as exc:
        flash(f"No se pudieron cargar tus torres: {exc}", "error")
        return redirect(url_for("cultivos.cultivos"))

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
        allowed_phases = _phase_options_for_form(form_data.nombre, form_data.variedad)
        if form_data.nombre not in CULTIVO_OPTIONS:
            form_data.errors.append("Selecciona un tipo de cultivo valido.")
        if form_data.variedad not in _variety_options_for_name(form_data.nombre):
            form_data.errors.append("Selecciona una variedad valida para el cultivo elegido.")
        if form_data.estado.lower() not in allowed_phases:
            form_data.errors.append("Selecciona una etapa valida para la variedad elegida.")
        if not any(item["id_torre"] == form_data.torre_id for item in torres):
            form_data.errors.append("Selecciona una torre valida para este cultivo.")

        if form_data.is_valid():
            try:
                update_cultivo(
                    cid,
                    usuario_id=user_id,
                    torre_id=form_data.torre_id,
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                sync_cultivo_phase_options(cid, form_data.variedad)
                flash("Cultivo actualizado correctamente.", "success")
                return redirect(url_for("cultivos.cultivos"))
            except Error as exc:
                flash(f"No se pudo actualizar el cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = CultivoFormData.from_mysql_cultivo(
            {
                "torre_id": cultivo.torre_id,
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
        torres=torres,
        nombre_options=list(CULTIVO_OPTIONS.keys()),
        variedad_options_by_nombre=_build_variety_options_by_name(),
        phase_options_by_variety=_build_phase_options_by_variety(),
    )


@cultivos_bp.route("/cultivos/borrar/<int:cid>", methods=("POST",))
@login_required
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
