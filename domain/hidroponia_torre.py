"""
Perfiles agronomicos para torres hidroponicas verticales (hoja verde / lechuga tipo).
Valores orientativos para invernadero controlado; ajustar segun variedad y sensor calibrado.
"""

from __future__ import annotations

# Ventana por defecto torre vertical — hoja verde (NFT / cascada en columna)
DEFAULT_LEAFY_PROFILE = {
    "ph_min": 5.5,
    "ph_max": 6.5,
    "ec_min": 1.0,
    "ec_max": 1.8,
    "temperatura_agua_min": 18.0,
    "temperatura_agua_max": 23.0,
    "temperatura_aire_min": 18.0,
    "temperatura_aire_max": 26.0,
    "humedad_aire_min": 50.0,
    "humedad_aire_max": 70.0,
    "luminosidad_min": 200.0,
    "irrigation_on_minutes": 5,
    "irrigation_off_minutes": 25,
    "notas": "Perfil generico hoja verde en torre vertical.",
}

# Perfiles por fase fenologica (claves normalizadas en minusculas)
PHASE_PROFILES: dict[str, dict] = {
    "germinacion": {
        "ph_min": 5.8,
        "ph_max": 6.2,
        "ec_min": 0.6,
        "ec_max": 1.0,
        "temperatura_agua_min": 20.0,
        "temperatura_agua_max": 24.0,
        "irrigation_on_minutes": 3,
        "irrigation_off_minutes": 45,
        "dias_referencia": 3,
        "notas": "Alta humedad ambiental; evitar EC alta. Luz baja hasta emergencia.",
    },
    "plantula": {
        "ph_min": 5.6,
        "ph_max": 6.2,
        "ec_min": 0.8,
        "ec_max": 1.2,
        "temperatura_agua_min": 19.0,
        "temperatura_agua_max": 23.0,
        "irrigation_on_minutes": 5,
        "irrigation_off_minutes": 30,
        "dias_referencia": 7,
        "notas": "Transplante a torre cuando raiz primaria visible y 2-3 hojas verdaderas.",
    },
    "desarrollo foliar": {
        "ph_min": 5.5,
        "ph_max": 6.5,
        "ec_min": 1.2,
        "ec_max": 1.8,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 22.0,
        "irrigation_on_minutes": 10,
        "irrigation_off_minutes": 20,
        "dias_referencia": 14,
        "notas": "Maxima demanda de N y Ca. Vigilar oxigenacion en raiz (temp. agua).",
    },
    "formacion de bola": {
        "ph_min": 5.5,
        "ph_max": 6.4,
        "ec_min": 1.2,
        "ec_max": 1.9,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 22.0,
        "irrigation_on_minutes": 12,
        "irrigation_off_minutes": 18,
        "dias_referencia": 10,
        "notas": "Compactacion del cogollo; reducir estrés térmico y variacion EC.",
    },
    "formacion de cogollo": {
        "ph_min": 5.5,
        "ph_max": 6.4,
        "ec_min": 1.2,
        "ec_max": 1.9,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 22.0,
        "irrigation_on_minutes": 12,
        "irrigation_off_minutes": 18,
        "dias_referencia": 10,
        "notas": "Equivalente a formacion de bola en lechugas tipo romana.",
    },
    "desarrollo resistente": {
        "ph_min": 5.6,
        "ph_max": 6.5,
        "ec_min": 1.3,
        "ec_max": 2.0,
        "temperatura_agua_min": 17.0,
        "temperatura_agua_max": 24.0,
        "irrigation_on_minutes": 12,
        "irrigation_off_minutes": 18,
        "dias_referencia": 12,
        "notas": "Variedades resistentes al calor; ventilar y evitar >26 °C sostenido.",
    },
    "cosecha": {
        "ph_min": 5.8,
        "ph_max": 6.5,
        "ec_min": 0.8,
        "ec_max": 1.4,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 22.0,
        "irrigation_on_minutes": 8,
        "irrigation_off_minutes": 30,
        "dias_referencia": 3,
        "notas": "Reducir EC 24-48 h antes de cosecha mejora sabor. Registrar peso y fecha.",
    },
    "cosecha continua": {
        "ph_min": 5.5,
        "ph_max": 6.5,
        "ec_min": 1.0,
        "ec_max": 1.7,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 22.0,
        "irrigation_on_minutes": 10,
        "irrigation_off_minutes": 20,
        "dias_referencia": 21,
        "notas": "Cosecha de hojas exteriores; mantener EC estable entre cortes.",
    },
    "ramificacion": {
        "ph_min": 5.5,
        "ph_max": 6.5,
        "ec_min": 1.1,
        "ec_max": 1.8,
        "temperatura_agua_min": 18.0,
        "temperatura_agua_max": 23.0,
        "irrigation_on_minutes": 10,
        "irrigation_off_minutes": 20,
        "dias_referencia": 14,
        "notas": "Albahaca y aromaticas: pinche puntas para ramificar.",
    },
}

# Ajustes por tipo de cultivo (nombre normalizado)
CROP_ADJUSTMENTS: dict[str, dict] = {
    "albahaca": {"ec_max": 2.2, "temperatura_agua_max": 24.0, "notas": "Tolera EC algo mayor; evitar floracion."},
    "acelga": {"ec_max": 2.4, "irrigation_on_minutes": 15, "notas": "Mayor consumo hídrico; cosecha por rebrote."},
    "espinaca": {"temperatura_agua_max": 21.0, "notas": "Prefiere agua mas fresca; riesgo de marchitamiento si >24 °C."},
    "rucula": {"ec_min": 1.0, "ec_max": 2.0, "notas": "Sabor picante sube con EC alta y estrés."},
}


def normalize_fase(fase: str) -> str:
    return (fase or "").strip().lower()


def normalize_cultivo(nombre: str) -> str:
    return (nombre or "").strip().lower()


def phase_profile_for(fase: str, cultivo_nombre: str = "") -> dict:
    profile = dict(DEFAULT_LEAFY_PROFILE)
    phase_key = normalize_fase(fase)
    if phase_key in PHASE_PROFILES:
        profile.update(PHASE_PROFILES[phase_key])

    cultivo_key = normalize_cultivo(cultivo_nombre)
    for crop_key, adjustment in CROP_ADJUSTMENTS.items():
        if crop_key in cultivo_key:
            profile.update(adjustment)
            break

    profile["fase"] = phase_key or fase
    return profile


def merge_control_with_phase_profile(config: dict, fase: str, cultivo_nombre: str = "") -> dict:
    if not config:
        return config
    profile = phase_profile_for(fase, cultivo_nombre)
    merged = dict(config)
    numeric_keys = (
        "ph_min",
        "ph_max",
        "ec_min",
        "ec_max",
        "temperatura_agua_min",
        "temperatura_agua_max",
        "irrigation_on_minutes",
        "irrigation_off_minutes",
    )
    for key in numeric_keys:
        if key in profile:
            merged[key] = profile[key]
    merged["perfil_fase"] = profile.get("fase")
    merged["perfil_notas"] = profile.get("notas", "")
    merged["perfil_dias_referencia"] = profile.get("dias_referencia")
    return merged
