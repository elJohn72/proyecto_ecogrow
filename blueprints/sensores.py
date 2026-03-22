from flask import Blueprint, current_app, flash, jsonify, render_template, request, url_for
from mysql.connector import Error

from Conexión import (
    fetch_active_cycle_by_torre,
    fetch_cultivos,
    fetch_sensor_readings_by_torre,
    fetch_latest_sensor_reading_by_torre,
    insert_sensor_reading,
)

from .shared import current_torre, login_required, parse_optional_float, tower_required

sensores_bp = Blueprint("sensores", __name__)


@sensores_bp.route("/sensores")
@login_required
@tower_required
def sensores():
    torre = current_torre()
    if torre is None:
        return render_template("sensores.html", historial=[], cultivos=[], ciclo_activo=None, torre=None, ultima_lectura=None, api_url=url_for("sensores.api_sensor_reading"))

    try:
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
        historial = fetch_sensor_readings_by_torre(torre["id_torre"], 10)
        cultivos_registrados = fetch_cultivos()
    except Error as exc:
        flash(f"No se pudo consultar las lecturas de sensores: {exc}", "error")
        ciclo_activo = None
        ultima_lectura = None
        historial = []
        cultivos_registrados = []

    return render_template(
        "sensores.html",
        ultima_lectura=ultima_lectura,
        historial=historial,
        cultivos=cultivos_registrados,
        ciclo_activo=ciclo_activo,
        torre=torre,
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


@sensores_bp.route("/irrigation")
@login_required
def irrigation():
    return render_template("irrigation.html")


@sensores_bp.route("/sustainability")
@login_required
def sustainability():
    return render_template("sustainability.html")
