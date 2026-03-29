import os

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from mysql.connector import Error

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

try:
    from Conexión import (
        apply_assistant_control_action,
        fetch_active_alerts_by_torre,
        fetch_active_cycle_by_torre,
        fetch_actuadores_by_torre,
        fetch_control_configuration,
        fetch_latest_sensor_reading_by_torre,
        fetch_recent_control_events,
        fetch_sensor_readings_by_torre,
        fetch_torre,
    )
except ModuleNotFoundError:
    from ..Conexión import (
        apply_assistant_control_action,
        fetch_active_alerts_by_torre,
        fetch_active_cycle_by_torre,
        fetch_actuadores_by_torre,
        fetch_control_configuration,
        fetch_latest_sensor_reading_by_torre,
        fetch_recent_control_events,
        fetch_sensor_readings_by_torre,
        fetch_torre,
    )

from .shared import current_torre, is_admin_mode, tower_required

ai_bp = Blueprint("ai", __name__)


def _format_metric(value, suffix: str = "", digits: int = 2) -> str:
    if value is None:
        return "Sin dato"
    return f"{float(value):.{digits}f}{suffix}"


def _build_snapshot(torre_id: int) -> dict:
    torre = fetch_torre(torre_id)
    return {
        "torre": torre,
        "ciclo": fetch_active_cycle_by_torre(torre_id),
        "lectura": fetch_latest_sensor_reading_by_torre(torre_id),
        "configuracion": fetch_control_configuration(torre_id),
        "alertas": fetch_active_alerts_by_torre(torre_id),
        "actuadores": fetch_actuadores_by_torre(torre_id),
        "eventos": fetch_recent_control_events(torre_id, 4),
        "historial": fetch_sensor_readings_by_torre(torre_id, 5),
    }


def _build_recommendation(snapshot: dict) -> dict:
    ciclo = snapshot["ciclo"]
    lectura = snapshot["lectura"]
    configuracion = snapshot["configuracion"]

    if not ciclo:
        return {
            "variable": "cultivo",
            "action": "Configurar cultivo activo",
            "reason": "La torre todavia no tiene un cultivo activo asociado.",
            "severity": "media",
            "can_execute": False,
        }

    if not lectura or not configuracion:
        return {
            "variable": "monitoreo",
            "action": "Esperar nueva telemetria",
            "reason": "Necesito lecturas recientes y configuracion de control para intervenir con seguridad.",
            "severity": "media",
            "can_execute": False,
        }

    rules = [
        (
            lectura.get("nivel_agua") is not None and float(lectura["nivel_agua"]) <= float(configuracion["nivel_minimo"]),
            {
                "variable": "nivel_agua",
                "action": "Recargar deposito",
                "reason": f"El nivel de agua esta en {_format_metric(lectura.get('nivel_agua'), '%')} y el minimo seguro es {_format_metric(configuracion['nivel_minimo'], '%')}.",
                "severity": "critica",
                "can_execute": True,
            },
        ),
        (
            lectura.get("ph") is not None and float(lectura["ph"]) < float(configuracion["ph_min"]),
            {
                "variable": "ph",
                "action": "Aplicar pH Up",
                "reason": f"El pH actual es {_format_metric(lectura.get('ph'))} y esta por debajo del minimo {_format_metric(configuracion['ph_min'])}.",
                "severity": "alta",
                "can_execute": True,
            },
        ),
        (
            lectura.get("ph") is not None and float(lectura["ph"]) > float(configuracion["ph_max"]),
            {
                "variable": "ph",
                "action": "Aplicar pH Down",
                "reason": f"El pH actual es {_format_metric(lectura.get('ph'))} y supera el maximo {_format_metric(configuracion['ph_max'])}.",
                "severity": "alta",
                "can_execute": True,
            },
        ),
        (
            lectura.get("ec") is not None and float(lectura["ec"]) < float(configuracion["ec_min"]),
            {
                "variable": "ec",
                "action": "Dosificar AB Mix",
                "reason": f"La EC esta en {_format_metric(lectura.get('ec'))} y se encuentra debajo del objetivo minimo {_format_metric(configuracion['ec_min'])}.",
                "severity": "media",
                "can_execute": True,
            },
        ),
        (
            lectura.get("ec") is not None and float(lectura["ec"]) > float(configuracion["ec_max"]),
            {
                "variable": "ec",
                "action": "Diluir con agua",
                "reason": f"La EC esta en {_format_metric(lectura.get('ec'))} y excede el maximo recomendado {_format_metric(configuracion['ec_max'])}.",
                "severity": "media",
                "can_execute": True,
            },
        ),
        (
            lectura.get("temperatura_agua") is not None
            and float(lectura["temperatura_agua"]) > float(configuracion["temperatura_agua_max"]),
            {
                "variable": "temperatura_agua",
                "action": "Aumentar frecuencia de riego",
                "reason": f"La temperatura del agua esta en {_format_metric(lectura.get('temperatura_agua'), ' C')} y supera el maximo {_format_metric(configuracion['temperatura_agua_max'], ' C')}.",
                "severity": "media",
                "can_execute": True,
            },
        ),
        (
            lectura.get("temperatura_agua") is not None
            and float(lectura["temperatura_agua"]) < float(configuracion["temperatura_agua_min"]),
            {
                "variable": "temperatura_agua",
                "action": "Reducir frecuencia de riego",
                "reason": f"La temperatura del agua esta en {_format_metric(lectura.get('temperatura_agua'), ' C')} y esta por debajo del minimo {_format_metric(configuracion['temperatura_agua_min'], ' C')}.",
                "severity": "baja",
                "can_execute": True,
            },
        ),
    ]

    for matched, recommendation in rules:
        if matched:
            return recommendation

    return {
        "variable": "estabilidad",
        "action": "Mantener monitoreo",
        "reason": "Los principales indicadores estan dentro de los rangos operativos configurados para la torre.",
        "severity": "ok",
        "can_execute": False,
    }


def _build_snapshot_summary(snapshot: dict) -> dict:
    torre = snapshot["torre"]
    ciclo = snapshot["ciclo"]
    lectura = snapshot["lectura"]
    alertas = snapshot["alertas"]
    actuadores = snapshot["actuadores"]

    return {
        "torre": torre["nombre"] if torre else "Sin torre",
        "cultivo": ciclo["cultivo_nombre"] if ciclo else "Sin cultivo activo",
        "fase": ciclo["fase"] if ciclo else "Sin fase",
        "ultima_lectura": lectura["fecha_registro"] if lectura else "Sin datos",
        "ph": _format_metric(lectura.get("ph") if lectura else None),
        "ec": _format_metric(lectura.get("ec") if lectura else None),
        "temperatura_agua": _format_metric(lectura.get("temperatura_agua") if lectura else None, " C"),
        "nivel_agua": _format_metric(lectura.get("nivel_agua") if lectura else None, "%"),
        "alertas_activas": len(alertas),
        "actuadores": [
            {
                "tipo": actuador["tipo"],
                "estado": actuador["estado"],
                "modo": actuador["modo"],
            }
            for actuador in actuadores
        ],
    }


def _build_local_reply(question: str, snapshot: dict, recommendation: dict) -> str:
    lectura = snapshot["lectura"]
    ciclo = snapshot["ciclo"]
    alertas = snapshot["alertas"]
    lower_question = question.lower()

    if not ciclo:
        return "No puedo evaluar la planta porque la torre aun no tiene un cultivo activo configurado. Primero asigna el cultivo y luego vuelvo a analizarla."

    if not lectura:
        return "Todavia no tengo telemetria reciente para evaluar la planta. En cuanto llegue una nueva lectura puedo indicarte estado, riesgos y accion sugerida."

    status_line = (
        f"Tu cultivo {ciclo['cultivo_nombre']} en fase {ciclo['fase']} registra pH { _format_metric(lectura.get('ph')) }, "
        f"EC { _format_metric(lectura.get('ec')) }, temperatura de agua { _format_metric(lectura.get('temperatura_agua'), ' C') } "
        f"y nivel { _format_metric(lectura.get('nivel_agua'), '%') }."
    )

    if "ph" in lower_question:
        return f"{status_line} Mi lectura puntual de pH es: {recommendation['reason']}"
    if "ec" in lower_question or "nutri" in lower_question:
        return f"{status_line} Sobre nutricion: {recommendation['reason']}"
    if "temper" in lower_question or "agua" in lower_question:
        return f"{status_line} Respecto al agua: {recommendation['reason']}"
    if "alerta" in lower_question or "riesgo" in lower_question:
        if alertas:
            return f"{status_line} Tienes {len(alertas)} alerta(s) activa(s). La accion prioritaria es: {recommendation['action']}. {recommendation['reason']}"
        return f"{status_line} No observo alertas activas en este momento. {recommendation['reason']}"

    return f"{status_line} Mi recomendacion actual es: {recommendation['action']}. {recommendation['reason']}"


def _build_gemini_reply(question: str, snapshot: dict, recommendation: dict) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if genai is None or not api_key:
        return None

    lectura = snapshot["lectura"]
    ciclo = snapshot["ciclo"]
    torre = snapshot["torre"]
    configuracion = snapshot["configuracion"]
    alertas = snapshot["alertas"]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
Eres el Agricultor IA de EcoGrow. Responde como un agronomo hidropónico claro y practico.
Contesta en espanol, maximo 6 lineas, sin inventar datos.

Pregunta del usuario: {question}
Torre: {torre['nombre'] if torre else 'Sin torre'}
Cultivo: {ciclo['cultivo_nombre'] if ciclo else 'Sin cultivo activo'}
Fase: {ciclo['fase'] if ciclo else 'Sin fase'}
Ultima lectura:
- pH: {lectura.get('ph') if lectura else 'N/A'}
- EC: {lectura.get('ec') if lectura else 'N/A'}
- Temperatura agua: {lectura.get('temperatura_agua') if lectura else 'N/A'}
- Nivel agua: {lectura.get('nivel_agua') if lectura else 'N/A'}
- Humedad aire: {lectura.get('humedad_aire') if lectura else 'N/A'}
- Luminosidad: {lectura.get('luminosidad') if lectura else 'N/A'}
Rangos configurados:
- pH: {configuracion['ph_min'] if configuracion else 'N/A'} - {configuracion['ph_max'] if configuracion else 'N/A'}
- EC: {configuracion['ec_min'] if configuracion else 'N/A'} - {configuracion['ec_max'] if configuracion else 'N/A'}
- Temperatura agua: {configuracion['temperatura_agua_min'] if configuracion else 'N/A'} - {configuracion['temperatura_agua_max'] if configuracion else 'N/A'}
- Nivel minimo: {configuracion['nivel_minimo'] if configuracion else 'N/A'}
Alertas activas: {len(alertas)}
Sugerencia deterministica del sistema:
- Accion: {recommendation['action']}
- Motivo: {recommendation['reason']}
- Ejecutable con permiso: {'si' if recommendation['can_execute'] else 'no'}

Da una respuesta util para el agricultor. Si la accion requiere permiso, indicarlo de forma natural.
"""

    try:
        response = model.generate_content(prompt)
    except Exception:
        return None

    text = getattr(response, "text", "") or ""
    return text.strip() or None


def _authorized_tower(torre_id: int) -> dict | None:
    torre = fetch_torre(torre_id)
    if not torre:
        return None
    return torre if torre["usuario_id"] == int(current_user.get_id()) else None


@ai_bp.route("/agricultor-ia")
@login_required
@tower_required
def agricultor_ia():
    torre = current_torre()
    if torre is None:
        return render_template("agricultor_ia.html", torre=None, snapshot=None, recommendation=None, ai_enabled=False)

    try:
        snapshot = _build_snapshot(torre["id_torre"])
    except Error as exc:
        return render_template(
            "agricultor_ia.html",
            torre=torre,
            snapshot=None,
            recommendation=None,
            ai_enabled=bool(genai and os.environ.get("GEMINI_API_KEY")),
            load_error=f"No se pudo cargar el asistente: {exc}",
        )

    return render_template(
        "agricultor_ia.html",
        torre=torre,
        snapshot=_build_snapshot_summary(snapshot),
        recommendation=_build_recommendation(snapshot),
        ai_enabled=bool(genai and os.environ.get("GEMINI_API_KEY")),
        load_error=None,
    )


@ai_bp.route("/api/agricultor-ia/chat", methods=["POST"])
@login_required
@tower_required
def agricultor_ia_chat():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("message", "")).strip()
    authorize_control = bool(payload.get("authorize_control"))

    torre = current_torre()
    if torre is None:
        return jsonify({"success": False, "error": "No hay una torre activa seleccionada."}), 400

    authorized_tower = _authorized_tower(torre["id_torre"])
    if not authorized_tower:
        return jsonify({"success": False, "error": "No tienes acceso a esta torre."}), 403

    if not question:
        return jsonify({"success": False, "error": "Escribe una pregunta para el asistente."}), 400

    if authorize_control and not is_admin_mode():
        return jsonify({"success": False, "error": "Solo el modo administrador puede autorizar acciones en la torre."}), 403

    try:
        snapshot = _build_snapshot(authorized_tower["id_torre"])
        recommendation = _build_recommendation(snapshot)
        reply = _build_gemini_reply(question, snapshot, recommendation) or _build_local_reply(question, snapshot, recommendation)
        execution = {
            "approved": authorize_control,
            "executed": False,
            "message": "La sugerencia quedo solo como recomendacion.",
        }

        if authorize_control and recommendation["can_execute"]:
            apply_assistant_control_action(
                authorized_tower["id_torre"],
                recommendation["variable"],
                recommendation["action"],
                f"Accion aprobada por {current_user.nombre} desde Agricultor IA. {recommendation['reason']}",
            )
            execution = {
                "approved": True,
                "executed": True,
                "message": f"Ejecute la accion sugerida: {recommendation['action']}.",
            }
            reply = f"{reply} Ya apliqué esa sugerencia en la torre porque me diste permiso."
        elif authorize_control:
            execution = {
                "approved": True,
                "executed": False,
                "message": "Esta recomendacion no requiere una accion automatica inmediata.",
            }
    except (Error, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify(
        {
            "success": True,
            "reply": reply,
            "recommendation": recommendation,
            "execution": execution,
            "snapshot": _build_snapshot_summary(snapshot),
            "provider": "gemini" if genai and os.environ.get("GEMINI_API_KEY") else "local",
        }
    )


@ai_bp.route("/api/ai_advice/<int:torre_id>", methods=["GET"])
@login_required
def ai_advice(torre_id):
    torre = _authorized_tower(torre_id)
    if not torre:
        return jsonify({"success": False, "error": "Acceso denegado o torre no encontrada"}), 403

    try:
        snapshot = _build_snapshot(torre_id)
        recommendation = _build_recommendation(snapshot)
        reply = _build_gemini_reply("Dame un consejo breve sobre mi planta.", snapshot, recommendation)
        if not reply:
            reply = _build_local_reply("como esta mi planta", snapshot, recommendation)
    except (Error, ValueError) as exc:
        return jsonify({"success": False, "error": f"Error de IA: {exc}"}), 500

    return jsonify({"success": True, "advice": reply, "recommendation": recommendation})
