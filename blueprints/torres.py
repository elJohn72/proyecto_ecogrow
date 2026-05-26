from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

try:
    from Conexión import (
        close_active_cycle,
        count_cycles_by_torre,
        fetch_archived_torres_by_user,
        fetch_active_cycle_by_torre,
        fetch_cultivo_phase_options,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_phase_options_map_for_user,
        fetch_torre,
        fetch_torres_by_user,
        register_torre,
        seed_default_phase_catalog_for_user,
        start_cultivo_cycle,
        update_active_cycle_phase,
        update_torre_estado,
        fetch_control_configuration,
        fetch_effective_control_configuration,
        fetch_harvests_by_torre,
        fetch_irrigation_schedule,
        register_harvest,
        update_torre_control_configuration,
        update_torre_irrigation_schedule,
    )
    from forms import CicloCultivoFormData, CosechaFormData, TorreControlFormData, TorreFormData
    from services import fetch_cultivo, fetch_cultivos
except ModuleNotFoundError:
    from ..Conexión import (
        close_active_cycle,
        count_cycles_by_torre,
        fetch_archived_torres_by_user,
        fetch_active_cycle_by_torre,
        fetch_cultivo_phase_options,
        fetch_cycles_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_phase_options_map_for_user,
        fetch_torre,
        fetch_torres_by_user,
        register_torre,
        seed_default_phase_catalog_for_user,
        start_cultivo_cycle,
        update_active_cycle_phase,
        update_torre_estado,
        fetch_control_configuration,
        fetch_effective_control_configuration,
        fetch_harvests_by_torre,
        fetch_irrigation_schedule,
        register_harvest,
        update_torre_control_configuration,
        update_torre_irrigation_schedule,
    )
    from ..forms import CicloCultivoFormData, CosechaFormData, TorreControlFormData, TorreFormData
    from ..services import fetch_cultivo, fetch_cultivos

from .shared import current_torre, current_user_id, login_required, tower_required

torres_bp = Blueprint("torres", __name__)
def _phase_options_map(user_id: int, ciclo_activo: dict | None = None) -> dict[str, list[str]]:
    options = fetch_phase_options_map_for_user(user_id)

    if ciclo_activo and ciclo_activo.get("cultivo_id") is not None:
        cultivo_id = str(ciclo_activo["cultivo_id"])
        fase_actual = str(ciclo_activo.get("fase", "")).strip().lower()
        fases = options.setdefault(cultivo_id, [])
        if fase_actual and fase_actual not in fases:
            fases.append(fase_actual)

    return options


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
                return redirect(url_for("cultivos.crear_cultivo"))
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


@torres_bp.route("/torres/cultivo/fase", methods=("GET", "POST"))
@login_required
@tower_required
def gestionar_fase_ciclo():
    torre = current_torre()
    user_id = current_user_id()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        cultivos = fetch_cultivos(user_id)
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"])
        phase_options_by_cultivo = _phase_options_map(user_id, ciclo_activo)
    except Error as exc:
        flash(f"No se pudo cargar el ciclo de cultivo: {exc}", "error")
        return redirect(url_for("torres.dashboard"))

    ciclo_form = CicloCultivoFormData()
    if ciclo_activo:
        ciclo_form = CicloCultivoFormData(
            cultivo_id=ciclo_activo["cultivo_id"],
            fase=ciclo_activo.get("fase", ""),
            notas=ciclo_activo.get("notas", ""),
        )

    if request.method == "POST":
        ciclo_form = CicloCultivoFormData.from_request(request.form)
        allowed_phases = phase_options_by_cultivo.get(str(ciclo_form.cultivo_id), [])
        if ciclo_form.cultivo_id is None or not any(
            c.id_cultivo == ciclo_form.cultivo_id for c in cultivos
        ):
            ciclo_form.errors.append("Selecciona un cultivo valido.")
        if ciclo_form.fase.lower() not in {fase.lower() for fase in allowed_phases}:
            ciclo_form.errors.append("Selecciona una etapa valida para este cultivo.")

        if ciclo_form.is_valid():
            try:
                if ciclo_activo:
                    update_active_cycle_phase(
                        torre["id_torre"],
                        ciclo_form.fase,
                        ciclo_form.notas,
                    )
                    flash("Fase del cultivo actualizada. Los rangos pH/EC del monitoreo usan el perfil de esta etapa.", "success")
                else:
                    start_cultivo_cycle(
                        torre["id_torre"],
                        ciclo_form.cultivo_id,
                        ciclo_form.fase,
                        ciclo_form.notas,
                    )
                    flash("Ciclo de cultivo iniciado en la torre activa.", "success")
                return redirect(url_for("torres.dashboard"))
            except (Error, ValueError) as exc:
                flash(f"No se pudo guardar la fase: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    perfil_agronomico = None
    if ciclo_activo:
        try:
            from domain.hidroponia_torre import phase_profile_for
        except ModuleNotFoundError:
            from ..domain.hidroponia_torre import phase_profile_for
        perfil_agronomico = phase_profile_for(
            ciclo_activo.get("fase", ""),
            ciclo_activo.get("cultivo_nombre", ""),
        )

    return render_template(
        "ciclo_form.html",
        titulo="Fase del cultivo en torre",
        accion="Guardar fase",
        ciclo=ciclo_form,
        cultivos=cultivos,
        ciclo_activo=ciclo_activo,
        historial_ciclos=historial_ciclos,
        phase_options_by_cultivo=phase_options_by_cultivo,
        perfil_agronomico=perfil_agronomico,
        errores=ciclo_form.errors,
    )


@torres_bp.route("/torres/cultivo", methods=("GET", "POST"))
@login_required
@tower_required
def elegir_cultivo_actual():
    return redirect(url_for("torres.gestionar_fase_ciclo"))


@torres_bp.route("/torres/cultivo/cosecha", methods=("GET", "POST"))
@login_required
@tower_required
def registrar_cosecha():
    torre = current_torre()
    user_id = current_user_id()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_cosechas = fetch_harvests_by_torre(torre["id_torre"], 8)
    except Error as exc:
        flash(f"No se pudo cargar la cosecha: {exc}", "error")
        return redirect(url_for("torres.dashboard"))

    if not ciclo_activo:
        flash("Primero inicia un ciclo de cultivo antes de registrar la cosecha.", "error")
        return redirect(url_for("torres.gestionar_fase_ciclo"))

    form_data = CosechaFormData()
    if request.method == "POST":
        form_data = CosechaFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                register_harvest(
                    torre["id_torre"],
                    user_id,
                    peso_kg=form_data.peso_kg,
                    plantas_cosechadas=form_data.plantas_cosechadas,
                    notas=form_data.notas,
                )
                flash(
                    f"Cosecha registrada: {form_data.peso_kg} kg. Ciclo cerrado y bomba en reposo.",
                    "success",
                )
                return redirect(url_for("torres.dashboard"))
            except (Error, ValueError) as exc:
                flash(f"No se pudo registrar la cosecha: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "cosecha_form.html",
        torre=torre,
        ciclo_activo=ciclo_activo,
        form_data=form_data,
        historial_cosechas=historial_cosechas,
        errores=form_data.errors,
    )


@torres_bp.route("/torres/configuracion", methods=("GET", "POST"))
@login_required
@tower_required
def configuracion_torre():
    torre = current_torre()
    user_id = current_user_id()
    if torre is None or user_id is None:
        return redirect(url_for("torres.torres"))

    try:
        config = fetch_control_configuration(torre["id_torre"])
        programacion = fetch_irrigation_schedule(torre["id_torre"])
        config_efectiva = fetch_effective_control_configuration(torre["id_torre"])
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo cargar la configuracion: {exc}", "error")
        return redirect(url_for("torres.dashboard"))

    form_data = TorreControlFormData.from_mysql(config, programacion)
    if request.method == "POST":
        form_data = TorreControlFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                update_torre_control_configuration(
                    torre["id_torre"],
                    module_size_mm=form_data.module_size_mm,
                    deposito_litros=form_data.deposito_litros,
                    bomba_modelo=form_data.bomba_modelo,
                    head_height_m=form_data.head_height_m,
                    ph_min=form_data.ph_min,
                    ph_max=form_data.ph_max,
                    ec_min=form_data.ec_min,
                    ec_max=form_data.ec_max,
                    temperatura_agua_min=form_data.temperatura_agua_min,
                    temperatura_agua_max=form_data.temperatura_agua_max,
                    nivel_minimo=form_data.nivel_minimo,
                    nivel_objetivo=form_data.nivel_objetivo,
                    irrigation_on_minutes=form_data.irrigation_on_minutes,
                    irrigation_off_minutes=form_data.irrigation_off_minutes,
                )
                update_torre_irrigation_schedule(
                    torre["id_torre"],
                    habilitado=form_data.riego_habilitado,
                    minutos_encendido=form_data.irrigation_on_minutes,
                    minutos_apagado=form_data.irrigation_off_minutes,
                    estrategia=form_data.estrategia_riego,
                )
                flash("Configuracion de torre y riego actualizada.", "success")
                return redirect(url_for("sensores.irrigation"))
            except (Error, ValueError) as exc:
                flash(f"No se pudo guardar la configuracion: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "torre_config_form.html",
        torre=torre,
        ciclo_activo=ciclo_activo,
        config_efectiva=config_efectiva,
        form_data=form_data,
        errores=form_data.errors,
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
    return redirect(url_for("cultivos.crear_cultivo"))


@torres_bp.route("/torres/inactivar/<int:torre_id>", methods=("POST",))
@login_required
def inactivar_torre(torre_id):
    user_id = current_user_id()
    if user_id is None:
        return redirect(url_for("auth.login"))

    try:
        torre = fetch_torre(torre_id)
        if not torre or torre["usuario_id"] != user_id:
            flash("La torre solicitada no pertenece a tu cuenta.", "error")
            return redirect(url_for("torres.torres"))

        if count_cycles_by_torre(torre_id, user_id) > 0:
            flash("No puedes inactivar esta torre porque tiene cultivos o historial asociados.", "error")
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
        session["torre_id"] = torre_id
        flash("Torre activada correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo activar la torre: {exc}", "error")
    return redirect(url_for("torres.torres"))


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
        config_fase = fetch_effective_control_configuration(torre["id_torre"])
        historial_cosechas = fetch_harvests_by_torre(torre["id_torre"], 5)
    except Error as exc:
        flash(f"No se pudo cargar el dashboard: {exc}", "error")
        cultivos = []
        ciclo_activo = None
        ultima_lectura = None
        config_fase = None
        historial_cosechas = []

    return render_template(
        "dashboard.html",
        cultivos=cultivos,
        ciclo_activo=ciclo_activo,
        torre=torre,
        ultima_lectura=ultima_lectura,
        config_fase=config_fase,
        historial_cosechas=historial_cosechas,
    )
