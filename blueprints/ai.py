import os
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

try:
    from Conexión import (
        fetch_torre,
        fetch_active_cycle_by_torre,
        fetch_latest_sensor_reading_by_torre,
    )
except ModuleNotFoundError:
    from ..Conexión import (
        fetch_torre,
        fetch_active_cycle_by_torre,
        fetch_latest_sensor_reading_by_torre,
    )

ai_bp = Blueprint("ai", __name__)

@ai_bp.route("/api/ai_advice/<int:torre_id>", methods=["GET"])
@login_required
def ai_advice(torre_id):
    if genai is None:
        return jsonify({"success": False, "error": "La integracion Gemini no esta instalada en este entorno."}), 503

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "Falta configurar GEMINI_API_KEY en un archivo .env para habilitar el Agrónomo Virtual."}), 400
        
    torre = fetch_torre(torre_id)
    if not torre or torre["usuario_id"] != current_user.id:
        return jsonify({"success": False, "error": "Acceso denegado o torre no encontrada"}), 403
        
    ciclo = fetch_active_cycle_by_torre(torre_id)
    lectura = fetch_latest_sensor_reading_by_torre(torre_id)
    
    if not ciclo or not lectura:
        return jsonify({"success": False, "error": "Requiere un cultivo activo y lecturas de sensores para el análisis IA."}), 400
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
Eres el "Agrónomo Virtual", un experto en agricultura hidropónica y análisis de datos en la plataforma EcoGrow Agritech.
Analiza la siguiente lectura en tiempo real y ofrece un consejo muy breve (máximo 2 líneas) y sumamente profesional, orientado a acciones específicas para el cultivo.

Cultivo actual: {ciclo['cultivo_nombre']}
Fase de cultivo: {ciclo['fase']}

Últimas lecturas del nodo sensor:
Temperatura del aire: {lectura.get('temperatura_aire', 'N/A')} °C
Humedad del aire: {lectura.get('humedad_aire', 'N/A')} %
Temperatura del agua: {lectura.get('temperatura_agua', 'N/A')} °C
pH: {lectura.get('ph', 'N/A')}
Conductividad Eléctrica (EC): {lectura.get('ec', 'N/A')}
Luminosidad: {lectura.get('luminosidad', 'N/A')} lux

Responde directamente con la evaluación y tu consejo accionable, sin relleno.
"""
    
    try:
        response = model.generate_content(prompt)
        advice = response.text.strip()
        return jsonify({"success": True, "advice": advice})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error de IA: {str(e)}"}), 500
