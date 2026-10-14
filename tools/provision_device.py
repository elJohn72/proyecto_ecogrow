#!/usr/bin/env python3
"""Herramienta oficial de aprovisionamiento de fábrica y vinculación de identidad EcoGrow 2.0.

Garantiza la correspondencia estricta 1:1 entre el hardware ESP32, la identidad NVS y la etiqueta física:
- Identifica el dispositivo mediante MAC real por protocolo serial de taller.
- Genera y programa una única clave PoP criptográfica de 8 caracteres Base32 en NVS (o reutiliza la ya provisionada).
- Realiza verificación obligatoria (readback) comprobando que la NVS del hardware coincide con la PoP.
- Genera etiqueta vectorial SVG oficial con código QR matricial real escaneable y PIN legible.
- Guarda artefactos con permisos restringidos (0600) en directorio protegido fuera de git.
- Subcomandos: provision, verify, read, generate.
"""
import argparse
import glob
import json
import os
import re
import secrets
import sys
import time

BASE32_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_secure_pop(length: int = 8) -> str:
    """Genera una clave PoP criptográficamente impredecible con entropía segura."""
    return "".join(secrets.choice(BASE32_CHARSET) for _ in range(length))


def normalize_mac(mac_raw: str) -> str:
    """Normaliza y valida una dirección MAC de 6 octetos hex."""
    clean = re.sub(r"[^0-9A-Fa-f]", "", mac_raw).upper()
    if len(clean) != 12:
        raise ValueError(f"Dirección MAC inválida: '{mac_raw}'. Se requieren 12 dígitos hexadecimales.")
    return ":".join(clean[i : i + 2] for i in range(0, 12, 2))


def derive_ble_name(mac_normalized: str) -> str:
    """Obtiene el nombre anunciado por el ESP32 a partir de los últimos dos octetos MAC."""
    parts = mac_normalized.split(":")
    return f"PROV_EcoGrow_{parts[4]}{parts[5]}"


def build_provisioning_payload(ble_name: str, pop: str, code: str = "") -> dict:
    """Construye el payload oficial JSON para aprovisionamiento BLE de EcoGrow."""
    payload = {
        "ver": "v1",
        "name": ble_name,
        "pop": pop.strip().upper(),
        "transport": "ble",
    }
    if code:
        payload["code"] = code.strip().upper()
    return payload


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
    # Token directo alfanumérico en Base32
    token = re.sub(r"[^23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjklmnpqrstuvwxyz]", "", clean).upper()
    return token


def parse_qr_payload(input_str: str) -> dict:
    """Extrae el payload completo (pop, code, name) de un JSON o PIN."""
    clean = input_str.strip()
    if clean.startswith("{") and clean.endswith("}"):
        try:
            data = json.loads(clean)
            return {
                "pop": str(data.get("pop", "")).strip().upper(),
                "code": str(data.get("code", "")).strip().upper(),
                "name": str(data.get("name", "")).strip(),
                "ver": str(data.get("ver", "v1")).strip(),
            }
        except json.JSONDecodeError:
            pass
    token = re.sub(r"[^23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjklmnpqrstuvwxyz]", "", clean).upper()
    return {"pop": token, "code": "", "name": "", "ver": "v1"}


def extract_pop_from_svg(svg_content: str) -> str | None:
    """Extrae el PIN PoP de un archivo SVG de etiqueta previamente generado."""
    # Buscar en comentario estructurado o en elemento pin-text
    match_payload = re.search(r'<!--\s*ECOGROW-QR-PAYLOAD:\s*(\{.*?\})\s*-->', svg_content)
    if match_payload:
        try:
            data = json.loads(match_payload.group(1))
            if "pop" in data:
                return str(data["pop"]).strip().upper()
        except json.JSONDecodeError:
            pass

    match_pin = re.search(r'class="pin-text"[^>]*>([23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{8})<', svg_content)
    if match_pin:
        return match_pin.group(1).strip().upper()

    return None


def extract_code_from_svg(svg_content: str) -> str | None:
    """Extrae el código único de torre de un archivo SVG de etiqueta previamente generado."""
    match_payload = re.search(r'<!--\s*ECOGROW-QR-PAYLOAD:\s*(\{.*?\})\s*-->', svg_content)
    if match_payload:
        try:
            data = json.loads(match_payload.group(1))
            if "code" in data:
                return str(data["code"]).strip().upper()
        except json.JSONDecodeError:
            pass

    match_code = re.search(r'NÚMERO DE SERIE:[^<]*<text[^>]*class="value"[^>]*>([^<]+)<', svg_content)
    if match_code:
        return match_code.group(1).strip().upper()

    return None


def generate_qr_svg_elements(payload_str: str, size: float = 120.0) -> tuple[int, str]:
    """Genera los elementos SVG del código QR matricial real para el payload indicado."""
    try:
        import qrcode
    except ImportError:
        raise RuntimeError("La librería 'qrcode' es requerida para generar códigos QR reales. Instálala con 'pip install qrcode'.")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    matrix_size = len(matrix)
    module_size = size / matrix_size

    rects = []
    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c]:
                x = c * module_size
                y = r * module_size
                rects.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{module_size:.2f}" height="{module_size:.2f}" fill="#000000"/>')

    return matrix_size, "\n      ".join(rects)


def generate_svg_label(mac: str, ble_name: str, pop: str, serial: str) -> str:
    """Genera una etiqueta vectorial SVG oficial con código QR matricial real y PIN legible."""
    payload_dict = build_provisioning_payload(ble_name, pop, serial)
    payload_json = json.dumps(payload_dict)

    _, qr_elements = generate_qr_svg_elements(payload_json, size=120.0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="270" viewBox="0 0 520 270">
  <!-- ECOGROW-QR-PAYLOAD: {payload_json} -->
  <defs>
    <style>
      .title {{ font-family: monospace, sans-serif; font-size: 15px; font-weight: bold; fill: #195C3D; }}
      .label {{ font-family: sans-serif; font-size: 10px; font-weight: bold; fill: #555555; }}
      .value {{ font-family: monospace, sans-serif; font-size: 12px; font-weight: bold; fill: #111111; }}
      .pin-box {{ fill: #E8F5E9; stroke: #2E7D32; stroke-width: 2; rx: 8; }}
      .pin-text {{ font-family: monospace, sans-serif; font-size: 22px; font-weight: bold; fill: #1B5E20; letter-spacing: 4px; }}
      .qr-box {{ fill: #FFFFFF; stroke: #2E7D32; stroke-width: 1.5; rx: 6; }}
      .footer {{ font-family: sans-serif; font-size: 8.5px; fill: #666666; }}
      .qr-label {{ font-family: sans-serif; font-size: 9px; font-weight: bold; fill: #2E7D32; text-anchor: middle; }}
    </style>
  </defs>
  <!-- Borde exterior de etiqueta -->
  <rect x="5" y="5" width="510" height="260" rx="12" fill="#FFFFFF" stroke="#CCCCCC" stroke-width="2"/>
  
  <!-- Encabezado de Marca -->
  <text x="25" y="32" class="title">🌱 EcoGrow 2.0 · Identidad Oficial de Fábrica</text>
  <line x1="25" y1="42" x2="495" y2="42" stroke="#E0E0E0" stroke-width="1.5"/>
  
  <!-- Bloque Izquierdo: Identidad Técnica -->
  <text x="25" y="65" class="label">DISPOSITIVO BLE:</text>
  <text x="135" y="65" class="value">{ble_name}</text>
  
  <text x="25" y="88" class="label">NÚMERO DE SERIE:</text>
  <text x="135" y="88" class="value">{serial}</text>
  
  <text x="25" y="111" class="label">MAC FÍSICA:</text>
  <text x="135" y="111" class="value">{mac}</text>
  
  <!-- Cuadro Destacado del PIN PoP -->
  <rect x="25" y="130" width="310" height="58" class="pin-box"/>
  <text x="35" y="148" class="label">CLAVE POP / PIN DE VINCULACIÓN FÍSICA:</text>
  <text x="35" y="174" class="pin-text">{pop}</text>
  
  <!-- Bloque Derecho: Código QR Matricial Real Escaneable -->
  <rect x="355" y="55" width="140" height="150" class="qr-box"/>
  <g transform="translate(365, 65)">
    <!-- QR Matrix Real -->
    <rect x="-5" y="-5" width="130" height="130" fill="#FFFFFF"/>
    {qr_elements}
  </g>
  <text x="425" y="200" class="qr-label">ESCANEAR CON LA APP</text>

  <!-- Pie de Instrucciones Oficiales -->
  <line x1="25" y1="202" x2="340" y2="202" stroke="#EAEAEA" stroke-width="1"/>
  <text x="25" y="218" class="footer">1. En la app Android EcoGrow toca 'Aprovisionar Torre por BLE' y selecciona {ble_name}.</text>
  <text x="25" y="232" class="footer">2. Ingresa este PIN o escanea el QR superior para transferir las credenciales WiFi.</text>
  <text x="25" y="246" class="footer">Recuperación WiFi: pulsa BOOT 3s-8s. La clave PoP se preserva inalterada en NVS.</text>
</svg>
"""


def save_secure_label(filepath: str, svg_content: str) -> None:
    """Guarda la etiqueta en disco aplicando permisos restringidos 0600 (solo lectura/escritura del propietario)."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_content)
    try:
        os.chmod(filepath, 0o600)
    except OSError:
        pass


class Esp32SerialClient:
    """Cliente serial oficial para comunicarse con el protocolo de taller de EcoGrow."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 3.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    @staticmethod
    def detect_ports() -> list[str]:
        """Detecta automáticamente los puertos seriales USB conectados."""
        patterns = [
            "/dev/cu.usbserial*",
            "/dev/cu.SLAB_USBtoUART*",
            "/dev/cu.wchusbserial*",
            "/dev/ttyUSB*",
            "/dev/ttyACM*",
        ]
        ports = []
        for pat in patterns:
            ports.extend(glob.glob(pat))
        return sorted(list(set(ports)))

    def connect(self) -> None:
        """Abre la conexión serial asegurando que no se mantenga en reset."""
        try:
            import serial
        except ImportError:
            raise RuntimeError("La librería 'pyserial' es requerida para la comunicación con el ESP32. Instálala con 'pip install pyserial'.")

        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def close(self) -> None:
        """Cierra la conexión serial."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_command(self, cmd: str) -> str:
        """Envía un comando al ESP32 y espera una respuesta que empiece por ECOGROW:."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Puerto serial no conectado.")

        self.ser.reset_input_buffer()
        self.ser.write((cmd.strip() + "\n").encode("utf-8"))
        self.ser.flush()

        t0 = time.time()
        while time.time() - t0 < self.timeout:
            line = self.ser.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("ECOGROW:"):
                return line

        sanitized_cmd = re.sub(r":(SET_POP|VERIFY_POP|SET_DEVICE_TOKEN):.*", r":\1:***", cmd.strip())
        raise TimeoutError(f"Tiempo de espera agotado ({self.timeout}s) sin respuesta del ESP32 para: {sanitized_cmd}")

    def get_identity(self) -> dict:
        """Consulta la identidad real del dispositivo mediante ECOGROW:IDENT?."""
        resp = self.send_command("ECOGROW:IDENT?")
        prefix = "ECOGROW:IDENT:"
        if not resp.startswith(prefix):
            raise ValueError(f"Respuesta inesperada al consultar identidad: {resp}")

        payload_str = resp[len(prefix) :].strip()
        data = json.loads(payload_str)
        return data

    def set_pop(self, pop: str) -> str:
        """Instala una clave PoP en la NVS del ESP32 mediante ECOGROW:SET_POP:<pop>."""
        clean_pop = pop.strip().upper()
        resp = self.send_command(f"ECOGROW:SET_POP:{clean_pop}")
        if resp.startswith("ECOGROW:SET_POP_ERR:"):
            raise ValueError(f"El ESP32 rechazó la clave PoP: {resp}")
        prefix = "ECOGROW:SET_POP_OK:"
        if not resp.startswith(prefix):
            raise ValueError(f"Respuesta inválida al configurar PoP: {resp}")

        data = json.loads(resp[len(prefix) :].strip())
        return data.get("pop", clean_pop)

    def verify_pop(self, pop: str) -> bool:
        """Verifica que la clave PoP coincida exactamente en el hardware mediante ECOGROW:VERIFY_POP:<pop>."""
        clean_pop = pop.strip().upper()
        resp = self.send_command(f"ECOGROW:VERIFY_POP:{clean_pop}")
        prefix = "ECOGROW:VERIFY:"
        if not resp.startswith(prefix):
            raise ValueError(f"Respuesta inválida al verificar PoP: {resp}")

        data = json.loads(resp[len(prefix) :].strip())
        return bool(data.get("match", False))

    def set_code(self, code: str) -> str:
        """Instala el código único de torre en la NVS del ESP32 mediante ECOGROW:SET_CODE:<code>."""
        clean_code = code.strip().upper()
        resp = self.send_command(f"ECOGROW:SET_CODE:{clean_code}")
        prefix = "ECOGROW:SET_CODE_OK:"
        if not resp.startswith(prefix):
            raise ValueError(f"El ESP32 rechazó el código de torre: {resp}")
        data = json.loads(resp[len(prefix) :].strip())
        return data.get("code", clean_code)

    def verify_code(self, code: str) -> bool:
        """Verifica que el código coincida en el hardware mediante ECOGROW:VERIFY_CODE:<code>."""
        clean_code = code.strip().upper()
        resp = self.send_command(f"ECOGROW:VERIFY_CODE:{clean_code}")
        prefix = "ECOGROW:VERIFY_CODE:"
        if not resp.startswith(prefix):
            raise ValueError(f"Respuesta inválida al verificar código: {resp}")
        data = json.loads(resp[len(prefix) :].strip())
        return bool(data.get("match", False))

    def set_device_token(self, token: str) -> bool:
        """Instala el token individual de dispositivo en NVS mediante ECOGROW:SET_DEVICE_TOKEN:<token>."""
        clean_token = token.strip()
        resp = self.send_command(f"ECOGROW:SET_DEVICE_TOKEN:{clean_token}")
        prefix = "ECOGROW:SET_TOKEN_OK:"
        if not resp.startswith(prefix):
            raise ValueError(f"El ESP32 rechazó el token de dispositivo: {resp}")
        data = json.loads(resp[len(prefix) :].strip())
        return bool(data.get("set", False))


def provision_hardware_device(
    port: str | None = None,
    desired_pop: str | None = None,
    desired_code: str | None = None,
    desired_token: str | None = None,
    force: bool = False,
    rotate_token: bool = False,
    out_dir: str = "docs/soporte/etiquetas",
    sync_db: bool = True,
) -> dict:
    """Ejecuta el flujo completo de aprovisionamiento de taller con verificación en hardware."""
    # 1. Determinar puerto
    selected_port = port
    if not selected_port:
        detected = Esp32SerialClient.detect_ports()
        if not detected:
            raise RuntimeError("No se detectó ningún ESP32 conectado. Conecta la placa por USB o especifica --port.")
        selected_port = detected[0]

    # 2. Conectar y leer identidad
    client = Esp32SerialClient(selected_port)
    client.connect()
    try:
        ident = client.get_identity()
        mac = normalize_mac(ident["mac"])
        ble_name = ident.get("ble_name", derive_ble_name(mac))
        existing_pop = ident.get("pop", "")
        has_valid_pop = ident.get("has_pop", False) and len(existing_pop) == 8
        has_existing_token = ident.get("has_token", False)

        # 3. Decidir PoP a instalar o conservar
        if has_valid_pop and not force and not desired_pop:
            target_pop = existing_pop
            action_taken = "identidad_existente_conservada"
        else:
            target_pop = desired_pop.strip().upper() if desired_pop else generate_secure_pop(8)
            client.set_pop(target_pop)
            action_taken = "nueva_identidad_instalada"

        # 4. Verificación obligatoria de coincidencia PoP en hardware
        match_ok = client.verify_pop(target_pop)
        if not match_ok:
            raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que la PoP no coincide con el valor programado.")

        # 5. Programar y verificar código único de torre canónico (rechazando placeholders de ejemplo)
        raw_code = desired_code or ident.get("code")
        if raw_code and raw_code.strip() not in ("", "TORRE-001", "EG-TORRE-01", "DUMMY"):
            serial_no = raw_code.strip().upper()
        else:
            serial_no = f"EG-TORRE-{mac.replace(':', '')[-6:]}".upper()

        client.set_code(serial_no)
        code_match = client.verify_code(serial_no)
        if not code_match:
            raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que el código no coincide.")

        # Pre-chequeo en base de datos si sync_db está activo
        existing_db_disp = None
        if sync_db:
            try:
                from Conexión.conexion import fetch_dispositivo_by_codigo
                existing_db_disp = fetch_dispositivo_by_codigo(serial_no)
                if existing_db_disp and existing_db_disp.get("estado") == "reclamada" and not force:
                    raise ValueError(f"El dispositivo '{serial_no}' ya fue reclamado por un usuario en la nube. Usa --force si deseas reasignarlo a fábrica.")
            except ImportError:
                pass

        # 6. Programar token individual de dispositivo (conservar existente salvo rotación explícita o force)
        if has_existing_token and not force and not rotate_token and not desired_token:
            dev_token = existing_db_disp.get("device_token") if existing_db_disp else None
            if not dev_token:
                dev_token = secrets.token_hex(24)
                set_ok = client.set_device_token(dev_token)
                if not set_ok:
                    raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El ESP32 rechazó la instalación del token de dispositivo.")
        else:
            dev_token = (desired_token or secrets.token_hex(24)).strip()
            set_ok = client.set_device_token(dev_token)
            if not set_ok:
                raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El ESP32 rechazó la instalación del token de dispositivo.")

        # 7. Registro obligatorio en base de datos de fábrica si sync_db es True
        db_registered = False
        if sync_db:
            from Conexión.conexion import register_dispositivo_fabrica
            register_dispositivo_fabrica(serial_no, mac, target_pop, dev_token, force=force)
            db_registered = True

        # 8. Generar y guardar etiqueta SVG con QR real y permisos 0600 (SOLO tras éxito en HW y DB)
        svg_content = generate_svg_label(mac, ble_name, target_pop, serial_no)
        out_filename = os.path.join(out_dir, f"{ble_name}_etiqueta.svg")
        save_secure_label(out_filename, svg_content)

        return {
            "status": "success",
            "action": action_taken,
            "port": selected_port,
            "mac": mac,
            "ble_name": ble_name,
            "serial": serial_no,
            "pop": target_pop,
            "device_token": dev_token,
            "label_file": out_filename,
            "verified": True,
            "db_registered": db_registered,
        }
    finally:
        client.close()


def verify_hardware_device(
    port: str | None = None,
    pop: str | None = None,
    code: str | None = None,
    label_path: str | None = None,
) -> dict:
    """Verifica que el ESP32 conectado coincida con un PIN PoP, código o con un archivo de etiqueta."""
    expected_pop = None
    expected_code = None
    if label_path:
        if not os.path.isfile(label_path):
            raise FileNotFoundError(f"Archivo de etiqueta no encontrado: {label_path}")
        with open(label_path, "r", encoding="utf-8") as f:
            content = f.read()
        expected_pop = extract_pop_from_svg(content)
        expected_code = extract_code_from_svg(content)
        if not expected_pop:
            raise ValueError(f"No se pudo extraer la PoP del archivo de etiqueta '{label_path}'.")
    else:
        if pop:
            expected_pop = pop.strip().upper()
        if code:
            expected_code = code.strip().upper()

    selected_port = port
    if not selected_port:
        detected = Esp32SerialClient.detect_ports()
        if not detected:
            raise RuntimeError("No se detectó ningún ESP32 conectado.")
        selected_port = detected[0]

    client = Esp32SerialClient(selected_port)
    client.connect()
    try:
        ident = client.get_identity()
        mac = normalize_mac(ident["mac"])
        ble_name = ident.get("ble_name", derive_ble_name(mac))
        device_pop = ident.get("pop", "")
        device_code = ident.get("code", "")

        match_pop = client.verify_pop(expected_pop) if expected_pop else (len(device_pop) == 8)
        match_code = client.verify_code(expected_code) if expected_code else True
        match = match_pop and match_code

        return {
            "port": selected_port,
            "mac": mac,
            "ble_name": ble_name,
            "device_pop": device_pop,
            "expected_pop": expected_pop,
            "device_code": device_code,
            "expected_code": expected_code,
            "match": match,
        }
    finally:
        client.close()


def generate_offline_label(
    mac: str,
    pop: str | None = None,
    serial: str | None = None,
    device_token: str | None = None,
    out_dir: str = "docs/soporte/etiquetas",
    sync_db: bool = False,
    force: bool = False,
) -> dict:
    """Genera una etiqueta en modo offline (para pruebas unitarias y entornos sin hardware físico)."""
    mac_norm = normalize_mac(mac)
    ble_name = derive_ble_name(mac_norm)
    pop_token = pop.strip().upper() if pop else generate_secure_pop(8)
    serial_no = serial or f"EG-TORRE-{mac_norm.replace(':', '')[-6:]}"
    dev_token = device_token or secrets.token_hex(24)

    svg_content = generate_svg_label(mac_norm, ble_name, pop_token, serial_no)
    out_filename = os.path.join(out_dir, f"{ble_name}_etiqueta.svg")
    save_secure_label(out_filename, svg_content)

    db_registered = False
    if sync_db:
        from Conexión.conexion import register_dispositivo_fabrica
        register_dispositivo_fabrica(serial_no, mac_norm, pop_token, dev_token, force=force)
        db_registered = True

    return {
        "status": "success",
        "mac": mac_norm,
        "ble_name": ble_name,
        "serial": serial_no,
        "pop": pop_token,
        "device_token": dev_token,
        "label_file": out_filename,
        "db_registered": db_registered,
    }


def main():
    parser = argparse.ArgumentParser(description="Aprovisionamiento de Fábrica EcoGrow 2.0")
    subparsers = parser.add_subparsers(dest="command")

    # 1. Subcomando provision
    prov_parser = subparsers.add_parser("provision", help="Aprovisionar hardware ESP32 y generar etiqueta verificada")
    prov_parser.add_argument("--port", help="Puerto serial del ESP32 (si no se indica, se autodetecta)")
    prov_parser.add_argument("--pop", help="Clave PoP específica a instalar (opcional; si se omite, se genera segura)")
    prov_parser.add_argument("--code", help="Código canónico específico a instalar (opcional)")
    prov_parser.add_argument("--rotate-token", action="store_true", help="Forzar rotación del token individual de dispositivo")
    prov_parser.add_argument("--no-db", action="store_true", help="Omitir registro en base de datos cloud")
    prov_parser.add_argument("--force", action="store_true", help="Sobreescribir identidad si ya existe en NVS")
    prov_parser.add_argument("--out", default="docs/soporte/etiquetas", help="Carpeta destino para guardar la etiqueta SVG")

    # 2. Subcomando verify
    ver_parser = subparsers.add_parser("verify", help="Verificar coincidencia entre hardware ESP32 y etiqueta/PIN")
    ver_parser.add_argument("--port", help="Puerto serial del ESP32")
    ver_parser.add_argument("--pop", help="PIN PoP a verificar contra el hardware")
    ver_parser.add_argument("--label", help="Ruta al archivo SVG de etiqueta para verificar contra el hardware")

    # 3. Subcomando read
    read_parser = subparsers.add_parser("read", help="Leer identidad instalada en el hardware sin modificarla")
    read_parser.add_argument("--port", help="Puerto serial del ESP32")

    # 4. Subcomando generate (offline)
    gen_parser = subparsers.add_parser("generate", help="Generar etiqueta offline con QR real para pruebas")
    gen_parser.add_argument("--mac", required=True, help="Dirección MAC física (ej: 44:1D:64:F8:70:C4)")
    gen_parser.add_argument("--pop", help="Clave PoP (opcional; se genera si no se especifica)")
    gen_parser.add_argument("--serial", help="Número de serie físico (opcional)")
    gen_parser.add_argument("--sync-db", action="store_true", default=False, help="Sincronizar en base de datos cloud de fábrica")
    gen_parser.add_argument("--force", action="store_true", default=False, help="Forzar sobreescritura en base de datos si ya existe")
    gen_parser.add_argument("--out", default="docs/soporte/etiquetas", help="Carpeta destino para guardar la etiqueta SVG")

    # Argumento común opcional para entornos de taller autorizados
    for p in [prov_parser, ver_parser, read_parser, gen_parser]:
        p.add_argument("--reveal-pop", action="store_true", help="Mostrar PIN PoP en terminal (desactivado por defecto por seguridad)")

    args = parser.parse_args()

    if args.command == "provision":
        try:
            res = provision_hardware_device(
                port=args.port,
                desired_pop=args.pop,
                desired_code=args.code,
                force=args.force,
                rotate_token=args.rotate_token,
                out_dir=args.out,
                sync_db=not args.no_db,
            )
            pop_display = res['pop'] if getattr(args, 'reveal_pop', False) else "[CONFIDENCIAL · Resguardado en etiqueta SVG (0600)]"
            print("=" * 60)
            print("🌱 APROVISIONAMIENTO DE FÁBRICA EXITOSO (HARDWARE VERIFICADO)")
            print("=" * 60)
            print(f"Puerto:          {res['port']}")
            print(f"Dispositivo BLE: {res['ble_name']}")
            print(f"MAC:             {res['mac']}")
            print(f"Número de Serie: {res['serial']}")
            print(f"PIN PoP:         {pop_display}")
            print(f"Acción:          {res['action']}")
            print(f"Verificación:    Hardware NVS coincide al 100%")
            print(f"Base de Datos:   {'Registrado en inventario cloud' if res['db_registered'] else 'Omitido / Offline'}")
            print(f"Etiqueta SVG:    {res['label_file']} (Permisos: 0600)")
            print("=" * 60)
        except Exception as exc:
            print(f"❌ ERROR DE APROVISIONAMIENTO: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "verify":
        try:
            res = verify_hardware_device(port=args.port, pop=args.pop, label_path=args.label)
            print("=" * 60)
            print("🔍 VERIFICACIÓN DE IDENTIDAD EN HARDWARE")
            print("=" * 60)
            print(f"Puerto:          {res['port']}")
            print(f"Dispositivo BLE: {res['ble_name']}")
            print(f"MAC:             {res['mac']}")
            if res.get("expected_pop"):
                print(f"Resultado:       {'✅ COINCIDENCIA CONFIRMADA' if res['match'] else '❌ DISCREPANCIA DETECTADA'}")
            else:
                print(f"Estado NVS:      {'✅ PoP Válida en NVS' if res['match'] else '❌ Sin PoP en NVS'}")
            print("=" * 60)
            if not res["match"]:
                sys.exit(1)
        except Exception as exc:
            print(f"❌ ERROR DE VERIFICACIÓN: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "read":
        try:
            ports = [args.port] if args.port else Esp32SerialClient.detect_ports()
            if not ports:
                raise RuntimeError("No se detectó ningún ESP32 conectado.")
            client = Esp32SerialClient(ports[0])
            client.connect()
            ident = client.get_identity()
            client.close()
            pop_display = ident.get('pop') if getattr(args, 'reveal_pop', False) else ("CONFIGURADA (8 chars)" if ident.get('has_pop') else "NO CONFIGURADA")
            print("=" * 60)
            print("📋 IDENTIDAD TÉCNICA LEÍDA DESDE ESP32")
            print("=" * 60)
            print(f"Puerto:          {ports[0]}")
            print(f"MAC:             {normalize_mac(ident['mac'])}")
            print(f"Dispositivo BLE: {ident.get('ble_name')}")
            print(f"Estado PoP:      {pop_display}")
            print(f"Tiene PoP:       {'Sí' if ident.get('has_pop') else 'No'}")
            print("=" * 60)
        except Exception as exc:
            print(f"❌ ERROR AL LEER DISPOSITIVO: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "generate":
        res = generate_offline_label(
            mac=args.mac,
            pop=args.pop,
            serial=args.serial,
            out_dir=args.out,
            sync_db=args.sync_db,
            force=args.force,
        )
        pop_display = res['pop'] if getattr(args, 'reveal_pop', False) else "[CONFIDENCIAL · Resguardado en etiqueta SVG (0600)]"
        print("=" * 60)
        print("🌱 ETIQUETA OFFLINE GENERADA CON CÓDIGO QR REAL")
        print("=" * 60)
        print(f"Dispositivo BLE: {res['ble_name']}")
        print(f"MAC:             {res['mac']}")
        print(f"Número de Serie: {res['serial']}")
        print(f"PIN PoP:         {pop_display}")
        print(f"Base de Datos:   {'Sincronizado' if res['db_registered'] else 'No modificada (Modo offline)'}")
        print(f"Etiqueta SVG:    {res['label_file']} (Permisos: 0600)")
        print("=" * 60)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
