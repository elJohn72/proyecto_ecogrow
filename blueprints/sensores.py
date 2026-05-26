from flask import Blueprint, current_app, flash, jsonify, render_template, request, url_for
from mysql.connector import Error

try:
    from Conexión import (
        fetch_torre,
        fetch_active_alerts_by_torre,
        fetch_active_cycle_by_torre,
        fetch_actuadores_by_torre,
        fetch_control_configuration,
        fetch_effective_control_configuration,
        fetch_irrigation_schedule,
        fetch_recent_control_events,
        fetch_sensor_readings_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_torres_by_user,
        insert_sensor_reading,
        set_actuador_estado,
        sync_iot_device,
    )
except ModuleNotFoundError:
    from ..Conexión import (
        fetch_torre,
        fetch_active_alerts_by_torre,
        fetch_active_cycle_by_torre,
        fetch_actuadores_by_torre,
        fetch_control_configuration,
        fetch_effective_control_configuration,
        fetch_irrigation_schedule,
        fetch_recent_control_events,
        fetch_sensor_readings_by_torre,
        fetch_latest_sensor_reading_by_torre,
        fetch_torres_by_user,
        insert_sensor_reading,
        set_actuador_estado,
        sync_iot_device,
    )

from .shared import current_torre, current_user_id, login_required, parse_optional_float

sensores_bp = Blueprint("sensores", __name__)


def _value_state(value, minimum, maximum):
    if value is None:
        return {"label": "Sin dato", "tone": "muted", "detail": "Esperando telemetria"}
    numeric_value = float(value)
    if numeric_value < float(minimum):
        return {"label": "Bajo", "tone": "warning", "detail": f"Por debajo de {minimum}"}
    if numeric_value > float(maximum):
        return {"label": "Alto", "tone": "danger", "detail": f"Por encima de {maximum}"}
    return {"label": "Estable", "tone": "ok", "detail": f"Dentro de {minimum}-{maximum}"}


def _build_operations_context(torre, ultima_lectura, configuracion, alertas, actuadores, programacion, eventos):
    ph_state = _value_state(
        ultima_lectura.get("ph") if ultima_lectura else None,
        configuracion["ph_min"],
        configuracion["ph_max"],
    )
    ec_state = _value_state(
        ultima_lectura.get("ec") if ultima_lectura else None,
        configuracion["ec_min"],
        configuracion["ec_max"],
    )
    temperatura_state = _value_state(
        ultima_lectura.get("temperatura_agua") if ultima_lectura else None,
        configuracion["temperatura_agua_min"],
        configuracion["temperatura_agua_max"],
    )
    nivel_state = _value_state(
        ultima_lectura.get("nivel_agua") if ultima_lectura else None,
        configuracion["nivel_minimo"],
        100,
    )

    principal_evento = eventos[0] if eventos else None
    resumen_control = {
        "mode": configuracion["control_mode"].replace("_", " ").title(),
        "algoritmo": principal_evento["algoritmo"].upper() if principal_evento else "CONSENSO",
        "accion": principal_evento["accion_recomendada"] if principal_evento else "Mantener monitoreo",
        "motivo": principal_evento["motivo"] if principal_evento else "Sin eventos de control calculados todavia.",
        "salida_consenso": principal_evento["salida_consenso"] if principal_evento else 0,
        "variable": principal_evento["variable_control"].upper() if principal_evento else "SIN DATOS",
        "error": principal_evento["error_valor"] if principal_evento else 0,
    }

    riesgo_bomba = "Protegida"
    if ultima_lectura and ultima_lectura.get("nivel_agua") is not None:
        riesgo_bomba = "Riesgo en seco" if float(ultima_lectura["nivel_agua"]) <= float(configuracion["nivel_minimo"]) else "Caudal estable"

    return {
        "control": resumen_control,
        "sensor_states": {
            "ph": ph_state,
            "ec": ec_state,
            "temperatura_agua": temperatura_state,
            "nivel_agua": nivel_state,
        },
        "alert_count": len(alertas),
        "critical_count": len([alerta for alerta in alertas if alerta["severidad"] == "critica"]),
        "bomba_estado": next((act["estado"] for act in actuadores if act["tipo"] == "bomba_principal"), riesgo_bomba),
        "riego_resumen": f"{programacion['minutos_encendido']} min ON / {programacion['minutos_apagado']} min OFF",
        "consenso_resumen": f"{int(float(configuracion['consenso_pid_weight']) * 100)}/{int(float(configuracion['consenso_fuzzy_weight']) * 100)} PID-Fuzzy",
        "torre_specs": f"Modulo {configuracion['module_size_mm']} mm · Deposito {configuracion['deposito_litros']} L",
        "head_height_ok": float(configuracion["head_height_m"]) <= 1.4,
    }


@sensores_bp.route("/sensores")
@login_required
def sensores():
    user_id = current_user_id()
    torre_activa = current_torre()
    selected_filter = request.args.get("filter", "all").strip().lower()
    if selected_filter not in {"all", "alerts"}:
        selected_filter = "all"

    if user_id is None:
        return render_template(
            "sensores.html",
            monitor_items=[],
            torre_activa=None,
            selected_filter=selected_filter,
            api_url=url_for("sensores.api_sensor_reading"),
        )

    monitor_items = []

    try:
        torres = fetch_torres_by_user(user_id)
    except Error as exc:
        flash(f"No se pudo consultar las lecturas de sensores: {exc}", "error")
        torres = []

    for torre in torres:
        try:
            ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
            ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
            historial = fetch_sensor_readings_by_torre(torre["id_torre"], 5)
            configuracion = fetch_effective_control_configuration(torre["id_torre"])
            alertas = fetch_active_alerts_by_torre(torre["id_torre"])
            actuadores = fetch_actuadores_by_torre(torre["id_torre"])
            programacion = fetch_irrigation_schedule(torre["id_torre"])
            eventos_control = fetch_recent_control_events(torre["id_torre"], 3)
        except Error as exc:
            monitor_items.append(
                {
                    "torre": torre,
                    "ciclo_activo": None,
                    "ultima_lectura": None,
                    "historial": [],
                    "configuracion": None,
                    "alertas": [],
                    "actuadores": [],
                    "programacion": None,
                    "eventos_control": [],
                    "operations": None,
                    "error": str(exc),
                    "is_selected": bool(torre_activa and torre_activa.get("id_torre") == torre.get("id_torre")),
                }
            )
            continue

        operations = None
        if configuracion and programacion:
            operations = _build_operations_context(
                torre,
                ultima_lectura,
                configuracion,
                alertas,
                actuadores,
                programacion,
                eventos_control,
            )

        monitor_items.append(
            {
                "torre": torre,
                "ciclo_activo": ciclo_activo,
                "ultima_lectura": ultima_lectura,
                "historial": historial,
                "configuracion": configuracion,
                "alertas": alertas,
                "actuadores": actuadores,
                "programacion": programacion,
                "eventos_control": eventos_control,
                "operations": operations,
                "error": None,
                "is_selected": bool(torre_activa and torre_activa.get("id_torre") == torre.get("id_torre")),
            }
        )

    if selected_filter == "alerts":
        monitor_items = [item for item in monitor_items if item["alertas"]]

    return render_template(
        "sensores.html",
        monitor_items=monitor_items,
        torre_activa=torre_activa,
        selected_filter=selected_filter,
        api_url=url_for("sensores.api_sensor_reading"),
    )


@sensores_bp.route("/api/sensores/lectura", methods=("POST",))
def api_sensor_reading():
    api_token = request.headers.get("X-API-Token", "").strip()
    if api_token != current_app.config["SENSOR_API_TOKEN"]:
        return jsonify({"ok": False, "error": "Token de dispositivo invalido."}), 401

    payload = request.get_json(silent=True) or {}
    dispositivo = str(payload.get("dispositivo", "")).strip()
    torre_codigo = str(payload.get("torre_codigo", "")).strip()

    if not dispositivo:
        return jsonify({"ok": False, "error": "El campo 'dispositivo' es obligatorio."}), 400
    if not torre_codigo:
        return jsonify({"ok": False, "error": "El campo 'torre_codigo' es obligatorio."}), 400

    try:
        lectura_id = insert_sensor_reading(
            torre_codigo=torre_codigo,
            dispositivo=dispositivo,
            temperatura_aire=parse_optional_float(payload.get("temperatura_aire")),
            humedad_aire=parse_optional_float(payload.get("humedad_aire")),
            temperatura_agua=parse_optional_float(payload.get("temperatura_agua")),
            ph=parse_optional_float(payload.get("ph")),
            ec=parse_optional_float(payload.get("ec")),
            nivel_agua=parse_optional_float(payload.get("nivel_agua")),
            luminosidad=parse_optional_float(payload.get("luminosidad")),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Error as exc:
        return jsonify({"ok": False, "error": f"No se pudo guardar la lectura: {exc}"}), 500

    return jsonify({"ok": True, "id_lectura": lectura_id}), 201


@sensores_bp.route("/api/iot/sync", methods=("POST",))
def api_iot_sync():
    api_token = request.headers.get("X-API-Token", "").strip()
    if api_token != current_app.config["SENSOR_API_TOKEN"]:
        return jsonify({"ok": False, "error": "Token de dispositivo invalido."}), 401

    payload = request.get_json(silent=True) or {}
    dispositivo = str(payload.get("dispositivo", "")).strip()
    torre_codigo = str(payload.get("torre_codigo", "")).strip()

    if not dispositivo:
        return jsonify({"ok": False, "error": "El campo 'dispositivo' es obligatorio."}), 400
    if not torre_codigo:
        return jsonify({"ok": False, "error": "El campo 'torre_codigo' es obligatorio."}), 400

    rele_raw = payload.get("rele_principal")
    rele_principal_on = None
    if rele_raw is not None:
        if isinstance(rele_raw, bool):
            rele_principal_on = rele_raw
        elif str(rele_raw).strip().lower() in {"1", "true", "on", "encendido", "encendida"}:
            rele_principal_on = True
        elif str(rele_raw).strip().lower() in {"0", "false", "off", "apagado", "apagada"}:
            rele_principal_on = False
        else:
            return jsonify({"ok": False, "error": "Valor invalido para rele_principal."}), 400

    try:
        result = sync_iot_device(
            torre_codigo=torre_codigo,
            dispositivo=dispositivo,
            rele_principal_on=rele_principal_on,
            temperatura_aire=parse_optional_float(payload.get("temperatura_aire")),
            humedad_aire=parse_optional_float(payload.get("humedad_aire")),
            temperatura_agua=parse_optional_float(payload.get("temperatura_agua")),
            ph=parse_optional_float(payload.get("ph")),
            ec=parse_optional_float(payload.get("ec")),
            nivel_agua=parse_optional_float(payload.get("nivel_agua")),
            luminosidad=parse_optional_float(payload.get("luminosidad")),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Error as exc:
        return jsonify({"ok": False, "error": f"No se pudo sincronizar el dispositivo: {exc}"}), 500

    return jsonify({"ok": True, **result}), 200


@sensores_bp.route("/monitoreo/rele/<int:torre_id>", methods=("POST",))
@login_required
def control_rele_torre(torre_id: int):
    user_id = current_user_id()
    if user_id is None:
        flash("Inicia sesion para controlar el rele.", "error")
        return redirect(url_for("auth.login"))

    estado = str(request.form.get("estado", "")).strip().lower()
    if estado not in {"encendida", "apagada"}:
        flash("Estado de rele invalido.", "error")
        return redirect(url_for("sensores.sensores"))

    try:
        torre = fetch_torre(torre_id)
        if not torre or int(torre["usuario_id"]) != user_id:
            flash("No tienes permiso para controlar esta torre.", "error")
            return redirect(url_for("sensores.sensores"))

        set_actuador_estado(
            torre_id,
            "bomba_principal",
            estado,
            modo="manual",
            ultimo_comando="panel_monitoreo",
        )
        flash(f"Rele programado en {estado}. El ESP32 aplicara el cambio en la proxima sincronizacion.", "success")
    except Error as exc:
        flash(f"No se pudo actualizar el rele: {exc}", "error")

    return redirect(url_for("sensores.sensores"))


@sensores_bp.route("/irrigation")
@login_required
def irrigation():
    torre = current_torre()
    if torre is None:
        return render_template("irrigation.html", torre=None, configuracion=None, programacion=None, actuadores=[])

    try:
        configuracion = fetch_effective_control_configuration(torre["id_torre"])
        programacion = fetch_irrigation_schedule(torre["id_torre"])
        actuadores = fetch_actuadores_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo consultar el riego automatico: {exc}", "error")
        configuracion = None
        programacion = None
        actuadores = []

    return render_template(
        "irrigation.html",
        torre=torre,
        configuracion=configuracion,
        programacion=programacion,
        actuadores=actuadores,
    )


@sensores_bp.route("/sustainability")
@login_required
def sustainability():
    return render_template("sustainability.html")
