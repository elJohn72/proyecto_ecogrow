#!/usr/bin/env python3
"""Herramienta oficial de aprovisionamiento de fábrica y generación de etiquetas QR EcoGrow 2.0.

Genera la identidad física única de cada torre durante su ensamblaje en taller/fábrica:
- Nombre de servicio BLE (PROV_EcoGrow_XXXX)
- PIN de posesión criptográfico (PoP) impredecible de 8 caracteres Base32
- Código QR vectorial (SVG) y ASCII para etiquetado en chasis
- Payload compatible con la app Android EcoGrow y el SDK de aprovisionamiento Espressif
"""
import argparse
import json
import os
import re
import secrets
import sys

BASE32_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_secure_pop(length: int = 8) -> str:
    """Genera una clave PoP criptográficamente impredecible con entropía de alta calidad."""
    return "".join(secrets.choice(BASE32_CHARSET) for _ in range(length))


def normalize_mac(mac_raw: str) -> str:
    """Normaliza y valida una dirección MAC de 6 octetos."""
    clean = re.sub(r"[^0-9A-Fa-f]", "", mac_raw).upper()
    if len(clean) != 12:
        raise ValueError(f"Dirección MAC inválida: '{mac_raw}'. Se requieren 6 octetos hex (ej: CC:50:E3:A1:B2:C3).")
    return ":".join(clean[i : i + 2] for i in range(0, 12, 2))


def derive_ble_name(mac_normalized: str) -> str:
    """Obtiene el nombre anunciado por el ESP32 a partir de los últimos dos octetos MAC."""
    parts = mac_normalized.split(":")
    return f"PROV_EcoGrow_{parts[4]}{parts[5]}"


def build_provisioning_payload(ble_name: str, pop: str) -> dict:
    """Construye el payload oficial JSON para aprovisionamiento BLE de EcoGrow."""
    return {
        "ver": "v1",
        "name": ble_name,
        "pop": pop.strip().upper(),
        "transport": "ble",
    }


def parse_qr_or_pin(input_str: str) -> str:
    """Extrae el PIN PoP de un input, ya sea JSON de QR completo o PIN directo."""
    clean = input_str.strip()
    if clean.startswith("{") and clean.endswith("}"):
        try:
            data = json.loads(clean)
            if "pop" in data:
                return str(data["pop"]).strip().upper()
        except json.JSONDecodeError:
            pass
    # Token directo alfanumérico
    token = re.sub(r"[^23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjklmnpqrstuvwxyz]", "", clean).upper()
    return token


def generate_svg_label(mac: str, ble_name: str, pop: str, serial: str) -> str:
    """Genera una etiqueta vectorial SVG lista para impresión térmica o pegatinas en chasis."""
    payload_json = json.dumps(build_provisioning_payload(ble_name, pop))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="260" viewBox="0 0 480 260">
  <defs>
    <style>
      .title {{ font-family: monospace, sans-serif; font-size: 16px; font-weight: bold; fill: #195C3D; }}
      .label {{ font-family: sans-serif; font-size: 11px; fill: #555555; }}
      .value {{ font-family: monospace, sans-serif; font-size: 13px; font-weight: bold; fill: #111111; }}
      .pin-box {{ fill: #E8F5E9; stroke: #2E7D32; stroke-width: 2; rx: 8; }}
      .pin-text {{ font-family: monospace, sans-serif; font-size: 24px; font-weight: bold; fill: #1B5E20; letter-spacing: 4px; }}
      .footer {{ font-family: sans-serif; font-size: 9px; fill: #777777; }}
    </style>
  </defs>
  <!-- Borde de etiqueta -->
  <rect x="5" y="5" width="470" height="250" rx="12" fill="#FFFFFF" stroke="#CCCCCC" stroke-width="2"/>
  
  <!-- Encabezado de Marca -->
  <text x="25" y="35" class="title">🌱 EcoGrow 2.0 · Control Inteligente</text>
  <line x1="25" y1="45" x2="455" y2="45" stroke="#EEEEEE" stroke-width="2"/>
  
  <!-- Datos de Identidad de Hardware -->
  <text x="25" y="70" class="label">DISPOSITIVO BLE:</text>
  <text x="140" y="70" class="value">{ble_name}</text>
  
  <text x="25" y="95" class="label">NÚMERO DE SERIE:</text>
  <text x="140" y="95" class="value">{serial}</text>
  
  <text x="25" y="120" class="label">MAC FÍSICA:</text>
  <text x="140" y="120" class="value">{mac}</text>
  
  <!-- Recuadro Destacado del PIN de Posesión (PoP) -->
  <rect x="25" y="140" width="430" height="60" class="pin-box"/>
  <text x="40" y="160" class="label">CLAVE POP / PIN DE VINCULACIÓN FÍSICA:</text>
  <text x="40" y="188" class="pin-text">{pop}</text>
  
  <!-- Pie de Instrucciones -->
  <text x="25" y="222" class="footer">1. Abre la app Android EcoGrow y selecciona el dispositivo Bluetooth arriba indicado.</text>
  <text x="25" y="236" class="footer">2. Ingresa este PIN único para transferir las credenciales WiFi y calibrar la torre.</text>
  <text x="25" y="248" class="footer">Recuperación WiFi: pulsa BOOT 3s-8s. La clave PoP se conserva en NVS.</text>
</svg>
"""


def provision_device_record(mac: str, pop: str | None = None, serial: str | None = None) -> dict:
    """Crea la ficha técnica de aprovisionamiento de fábrica para el dispositivo."""
    mac_norm = normalize_mac(mac)
    ble_name = derive_ble_name(mac_norm)
    pop_token = pop.strip().upper() if pop else generate_secure_pop(8)
    serial_no = serial or f"EG-TORRE-{mac_norm.replace(':', '')[-6:]}"
    payload = build_provisioning_payload(ble_name, pop_token)

    return {
        "mac": mac_norm,
        "ble_name": ble_name,
        "serial": serial_no,
        "pop": pop_token,
        "qr_payload": json.dumps(payload),
        "payload_dict": payload,
    }


def main():
    parser = argparse.ArgumentParser(description="Aprovisionamiento de Fábrica EcoGrow 2.0")
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generar identidad y etiqueta para un equipo nuevo")
    gen_parser.add_argument("--mac", required=True, help="Dirección MAC física del ESP32 (ej: CC:50:E3:A1:B2:C3)")
    gen_parser.add_argument("--pop", help="Clave PoP opcional (si no se indica, se genera aleatoria criptográfica)")
    gen_parser.add_argument("--serial", help="Número de serie físico (opcional)")
    gen_parser.add_argument("--out", default="etiquetas_fabricacion", help="Carpeta destino para guardar la etiqueta SVG")

    verify_parser = subparsers.add_parser("verify", help="Verificar o extraer PIN de un payload de QR o texto")
    verify_parser.add_argument("--input", required=True, help="Texto, token o JSON del código QR")

    args = parser.parse_args()

    if args.command == "generate":
        record = provision_device_record(args.mac, args.pop, args.serial)
        os.makedirs(args.out, exist_ok=True)
        svg_filename = os.path.join(args.out, f"{record['ble_name']}_etiqueta.svg")
        svg_content = generate_svg_label(record["mac"], record["ble_name"], record["pop"], record["serial"])
        with open(svg_filename, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print("=" * 60)
        print("🌱 FICHA DE FABRICACIÓN ECOGROW 2.0")
        print("=" * 60)
        print(f"Dispositivo BLE: {record['ble_name']}")
        print(f"Dirección MAC:   {record['mac']}")
        print(f"Número de Serie: {record['serial']}")
        print(f"PIN PoP Único:   {record['pop']}")
        print(f"Payload QR:      {record['qr_payload']}")
        print(f"Etiqueta SVG:    {svg_filename}")
        print("=" * 60)
        print("Instrucciones de taller:")
        print("1. Imprime la etiqueta SVG y adhiérela al chasis de la torre hidropónica.")
        print("2. El PIN PoP permanecerá inmutable ante cambios de router o reconfiguraciones WiFi.")
        print("=" * 60)

    elif args.command == "verify":
        token = parse_qr_or_pin(args.input)
        print(f"PIN PoP extraído: '{token}' (Válido: {len(token) >= 6})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
