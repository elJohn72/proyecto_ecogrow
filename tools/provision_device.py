#!/usr/bin/env python3
"""Herramienta oficial de aprovisionamiento de fábrica y vinculación de identidad EcoGrow 2.0.

Garantiza la correspondencia estricta 1:1 entre el hardware ESP32, la identidad NVS y la etiqueta física:
- Identifica el dispositivo mediante MAC real por protocolo serial de taller.
- Genera y programa una única clave PoP criptográfica de 8 caracteres Base32 en NVS (o reutiliza la ya provisionada).
- Realiza verificación obligatoria (readback) comprobando que la NVS del hardware coincide con la PoP.
- Genera etiqueta vectorial SVG oficial con código QR matricial real escaneable y PIN legible.
- Guarda artefactos con permisos restringidos (0600) en directorio protegido fuera de git.
- Subcomandos: provision, verify, read, generate, migrate-code, recover.
"""
import argparse
import glob
import hashlib
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

        sanitized_cmd = re.sub(r":(SET_POP|VERIFY_POP|SET_DEVICE_TOKEN|VERIFY_DEVICE_TOKEN):.*", r":\1:***", cmd.strip())
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

    def verify_device_token(self, token: str) -> bool:
        """Verifica que el token individual coincida en el hardware mediante ECOGROW:VERIFY_DEVICE_TOKEN:<token>."""
        clean_token = token.strip()
        resp = self.send_command(f"ECOGROW:VERIFY_DEVICE_TOKEN:{clean_token}")
        prefix = "ECOGROW:VERIFY_TOKEN:"
        if not resp.startswith(prefix):
            raise ValueError(f"Respuesta inválida al verificar token de dispositivo: {resp}")
        data = json.loads(resp[len(prefix) :].strip())
        return bool(data.get("match", False))


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_repo_on_path() -> None:
    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def _placeholder_code(code: str | None) -> bool:
    _ensure_repo_on_path()
    from tools.migrate_identities import is_placeholder_code
    return is_placeholder_code(code)


def _canonical_from_mac(mac: str) -> str:
    _ensure_repo_on_path()
    from tools.migrate_identities import derive_canonical_code
    return derive_canonical_code(mac)


def provision_state_dir(out_dir: str, state_dir: str | None = None) -> str:
    """Ruta del diario de taller. El directorio se crea solo al escribir un registro."""
    return state_dir or os.path.join(out_dir, ".provision-state")


def _journal_path(state_dir: str, mac: str, kind: str) -> str:
    safe = normalize_mac(mac).replace(":", "")
    return os.path.join(state_dir, f"{safe}.{kind}.json")


def _write_secret_journal(path: str, payload: dict) -> None:
    """Estado de recuperación. Contiene secretos de taller y queda en 0600, fuera de git."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    try:
        os.chmod(os.path.dirname(os.path.abspath(path)), 0o700)
    except OSError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_journal(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError("El registro de recuperación del taller está dañado.")
    return data


def _restore_field(client, field: str, previous) -> bool:
    try:
        if field == "pop":
            if not isinstance(previous, str) or len(previous) != 8:
                return False
            client.set_pop(previous)
            return client.verify_pop(previous) is True
        if field == "code":
            if not isinstance(previous, str) or _placeholder_code(previous):
                return False
            client.set_code(previous)
            return client.verify_code(previous) is True
        if field == "token":
            if not isinstance(previous, str) or len(previous) < 16:
                return False
            if client.set_device_token(previous) is not True:
                return False
            return client.verify_device_token(previous) is True
    except Exception:
        return False
    return False


def _rollback_mutations(client, journal: dict) -> tuple[list[str], list[str]]:
    previous = journal.get("previous") or {}
    restored: list[str] = []
    unrestored: list[str] = []
    for field in reversed(journal.get("mutated") or []):
        if _restore_field(client, field, previous.get(field)):
            restored.append(field)
        else:
            unrestored.append(field)
    return restored, unrestored


def _repair_text(unrestored: list[str]) -> str:
    fields = ", ".join(unrestored) if unrestored else "la identidad"
    return (
        f"Reparación requerida: no se pudo restaurar {fields}. "
        "La identidad previa no quedó conservada."
    )


def decide_provision_recovery(journal: dict, matches: dict, cloud: dict | None = None) -> str:
    """Elige keep, repair o rollback. Un commit ya visible en la nube no restaura el token viejo."""
    stage = journal.get("stage") or "mutating"
    mutated = list(journal.get("mutated") or [])
    cloud = cloud or {}
    intended = journal.get("intended") or {}
    previous = journal.get("previous") or {}

    def cloud_has_new(field: str) -> bool:
        if field == "token":
            if not cloud.get("token_is_intended"):
                return False
            if intended.get("token") and intended.get("token") == previous.get("token"):
                return stage == "db_committed"
            return True
        if field == "pop":
            if not cloud.get("pop_hash_is_intended"):
                return False
            if intended.get("pop") and intended.get("pop") == previous.get("pop"):
                return stage == "db_committed"
            return True
        if field == "code":
            return bool(cloud.get("code_is_intended")) and intended.get("code") != previous.get("code")
        return False

    committed = stage == "db_committed" or any(cloud_has_new(field) for field in mutated)
    if not committed:
        return "rollback"
    needed = {"token": "token_intended", "pop": "pop_intended", "code": "code_intended"}
    if mutated and all(matches.get(needed[field], False) for field in mutated if field in needed):
        return "keep"
    return "repair"


def _hardware_matches(client, journal: dict) -> dict:
    intended = journal.get("intended") or {}
    previous = journal.get("previous") or {}

    def verified(method: str, value) -> bool:
        if not isinstance(value, str) or not value:
            return False
        try:
            return getattr(client, method)(value) is True
        except Exception:
            return False

    return {
        "token_intended": verified("verify_device_token", intended.get("token")),
        "token_previous": verified("verify_device_token", previous.get("token")),
        "pop_intended": verified("verify_pop", intended.get("pop")),
        "pop_previous": verified("verify_pop", previous.get("pop")),
        "code_intended": verified("verify_code", intended.get("code")),
        "code_previous": verified("verify_code", previous.get("code")),
    }


def cloud_credential_view(journal: dict, row: dict | None) -> dict:
    """Booleans de coincidencia. No incluye el token ni el PIN."""
    if not row:
        return {}
    intended = journal.get("intended") or {}
    previous = journal.get("previous") or {}
    db_token = row.get("device_token")
    db_code = str(row.get("codigo_torre") or "").strip().upper()
    db_hash = row.get("pop_hash")
    view = {
        "token_is_intended": isinstance(intended.get("token"), str) and db_token == intended.get("token"),
        "token_is_previous": isinstance(previous.get("token"), str) and db_token == previous.get("token"),
        "code_is_intended": isinstance(intended.get("code"), str) and db_code == str(intended.get("code")).strip().upper(),
    }
    if isinstance(intended.get("pop"), str) and db_hash:
        view["pop_hash_is_intended"] = db_hash == hashlib.sha256(intended["pop"].encode("utf-8")).hexdigest()
    if isinstance(previous.get("pop"), str) and db_hash:
        view["pop_hash_is_previous"] = db_hash == hashlib.sha256(previous["pop"].encode("utf-8")).hexdigest()
    return view


def recover_open_provision(client, state_dir: str, mac: str, kind: str = "provision", cloud: dict | None = None) -> dict:
    """Restaura una mutación interrumpida y verifica cada campo. No anuncia éxito si falta uno."""
    path = _journal_path(state_dir, mac, kind)
    if not os.path.isfile(path):
        return {"status": "nothing_to_recover", "identity_conserved": True, "credentials_agree": True, "restored": [], "unrestored": []}
    journal = _read_journal(path)
    if journal.get("stage") == "complete":
        os.remove(path)
        return {"status": "nothing_to_recover", "identity_conserved": True, "credentials_agree": True, "restored": [], "unrestored": []}
    matches = _hardware_matches(client, journal)
    action = decide_provision_recovery(journal, matches, cloud)
    if action == "keep":
        os.remove(path)
        return {
            "status": "reconciled",
            "identity_conserved": False,
            "credentials_agree": True,
            "restored": [],
            "unrestored": [],
        }
    if action == "repair":
        journal["stage"] = "repair_required"
        journal["identity_conserved"] = False
        journal["credentials_agree"] = False
        _write_secret_journal(path, journal)
        return {
            "status": "repair_required",
            "identity_conserved": False,
            "credentials_agree": False,
            "restored": [],
            "unrestored": list(journal.get("mutated") or []),
        }
    restored, unrestored = _rollback_mutations(client, journal)
    if unrestored:
        journal["stage"] = "repair_required"
        journal["identity_conserved"] = False
        journal["unrestored"] = unrestored
        _write_secret_journal(path, journal)
        return {
            "status": "repair_required",
            "identity_conserved": False,
            "restored": restored,
            "unrestored": unrestored,
        }
    os.remove(path)
    return {"status": "restored", "identity_conserved": True, "restored": restored, "unrestored": []}


def _fail_after_rollback(client, journal_path: str, journal: dict, original: Exception) -> None:
    restored, unrestored = _rollback_mutations(client, journal)
    if not unrestored:
        if os.path.isfile(journal_path):
            os.remove(journal_path)
        raise original
    journal["stage"] = "repair_required"
    journal["identity_conserved"] = False
    journal["unrestored"] = unrestored
    journal["restored"] = restored
    _write_secret_journal(journal_path, journal)
    raise RuntimeError(f"{original} {_repair_text(unrestored)}") from None


def _begin_journal(state_dir: str, mac: str, kind: str, previous: dict) -> tuple[str, dict]:
    path = _journal_path(state_dir, mac, kind)
    journal = {
        "version": 1,
        "mac": normalize_mac(mac),
        "stage": "mutating",
        "previous": previous,
        "mutated": [],
        "identity_conserved": False,
    }
    _write_secret_journal(path, journal)
    return path, journal


def _note_mutation(path: str, journal: dict, field: str) -> None:
    if field not in journal["mutated"]:
        journal["mutated"].append(field)
    journal["stage"] = "mutating"
    _write_secret_journal(path, journal)


def provision_hardware_device(
    port: str | None = None,
    desired_pop: str | None = None,
    desired_code: str | None = None,
    desired_token: str | None = None,
    force: bool = False,
    rotate_token: bool = False,
    out_dir: str = "docs/soporte/etiquetas",
    sync_db: bool = True,
    state_dir: str | None = None,
) -> dict:
    """Aprovisiona con preflight, diario recuperable y readback de cada reversión."""
    selected_port = port
    if not selected_port:
        detected = Esp32SerialClient.detect_ports()
        if not detected:
            raise RuntimeError("No se detectó ningún ESP32 conectado. Conecta la placa por USB o especifica --port.")
        selected_port = detected[0]

    state_directory = provision_state_dir(out_dir, state_dir)
    client = Esp32SerialClient(selected_port)
    client.connect()
    try:
        ident = client.get_identity()
        mac = normalize_mac(ident["mac"])
        journal_preview_path = _journal_path(state_directory, mac, "provision")
        cloud_view = None
        if sync_db and os.path.isfile(journal_preview_path):
            preview = _read_journal(journal_preview_path)
            if preview.get("stage") != "complete":
                _ensure_repo_on_path()
                from Conexión.conexion import fetch_dispositivo_by_mac
                cloud_view = cloud_credential_view(preview, fetch_dispositivo_by_mac(mac))
        recovery = recover_open_provision(client, state_directory, mac, cloud=cloud_view)
        if recovery["status"] == "repair_required":
            raise RuntimeError(_repair_text(recovery["unrestored"]))
        if recovery["status"] in {"restored", "reconciled"}:
            ident = client.get_identity()

        ble_name = ident.get("ble_name", derive_ble_name(mac))
        existing_pop = ident.get("pop", "") or ""
        has_valid_pop = bool(ident.get("has_pop", False)) and len(existing_pop) == 8
        has_existing_token = bool(ident.get("has_token", False))
        current_code = (ident.get("code") or "").strip().upper()

        raw_code = desired_code or (current_code if current_code and not _placeholder_code(current_code) else "")
        serial_no = raw_code.strip().upper() if raw_code else _canonical_from_mac(mac)

        existing_db_disp = None
        if sync_db:
            _ensure_repo_on_path()
            from Conexión.conexion import fetch_dispositivo_by_codigo, fetch_dispositivo_by_mac
            existing_db_disp = fetch_dispositivo_by_codigo(serial_no) or fetch_dispositivo_by_mac(mac)
            if existing_db_disp and existing_db_disp.get("estado") == "reclamada" and not force:
                raise ValueError(
                    f"El dispositivo '{serial_no}' ya fue reclamado por un usuario en la nube. "
                    "Usa --force solo si el taller va a reasignarlo a fábrica."
                )

        previous_token: str | None = None
        new_token_to_write: str | None = None
        final_token_for_db: str | None = None

        if sync_db:
            db_token = existing_db_disp.get("device_token") if existing_db_disp else None
            if has_existing_token and db_token:
                token_matches = client.verify_device_token(db_token)
                if token_matches:
                    previous_token = db_token
                    if rotate_token or desired_token:
                        new_token_to_write = (desired_token or secrets.token_hex(24)).strip()
                        final_token_for_db = new_token_to_write
                    else:
                        new_token_to_write = None
                        final_token_for_db = db_token
                else:
                    if not force and not rotate_token and not desired_token:
                        raise RuntimeError(
                            f"DESINCRONIZACIÓN DE TOKEN: El token físico del ESP32 no coincide con el token "
                            f"registrado en la base de datos para '{serial_no}'. Usa --rotate-token o --force para sincronizar."
                        )
                    new_token_to_write = (desired_token or secrets.token_hex(24)).strip()
                    final_token_for_db = new_token_to_write
            else:
                new_token_to_write = (desired_token or secrets.token_hex(24)).strip()
                final_token_for_db = new_token_to_write
        else:
            if has_existing_token and not rotate_token and not desired_token:
                new_token_to_write = None
                final_token_for_db = None
            else:
                new_token_to_write = (desired_token or secrets.token_hex(24)).strip()
                final_token_for_db = new_token_to_write

        requested_pop = desired_pop.strip().upper() if desired_pop else None
        replace_pop = (not has_valid_pop) or force or (requested_pop is not None and requested_pop != existing_pop.strip().upper())
        target_pop = existing_pop if not replace_pop else (requested_pop or generate_secure_pop(8))
        replace_code = current_code != serial_no
        journal_path = ""
        journal: dict | None = None

        def ensure_journal() -> tuple[str, dict]:
            nonlocal journal_path, journal
            if journal is None:
                journal_path, journal = _begin_journal(
                    state_directory,
                    mac,
                    "provision",
                    {"pop": existing_pop if has_valid_pop else None, "code": current_code or None, "token": previous_token},
                )
            return journal_path, journal

        if replace_pop:
            path, active = ensure_journal()
            _note_mutation(path, active, "pop")
            try:
                client.set_pop(target_pop)
            except Exception:
                _fail_after_rollback(
                    client, path, active,
                    RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que la PoP no coincide con el valor programado."),
                )
            if client.verify_pop(target_pop) is not True:
                _fail_after_rollback(
                    client, path, active,
                    RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que la PoP no coincide con el valor programado."),
                )
        elif client.verify_pop(target_pop) is not True:
            raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que la PoP no coincide con el valor programado.")

        if replace_code:
            path, active = ensure_journal()
            _note_mutation(path, active, "code")
            client.set_code(serial_no)
            if client.verify_code(serial_no) is not True:
                _fail_after_rollback(
                    client, path, active,
                    RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que el código no coincide."),
                )
        elif client.verify_code(serial_no) is not True:
            raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que el código no coincide.")

        if new_token_to_write is not None:
            path, active = ensure_journal()
            _note_mutation(path, active, "token")
            set_ok = False
            try:
                set_ok = client.set_device_token(new_token_to_write) is True
            except Exception:
                _fail_after_rollback(
                    client, path, active,
                    RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El ESP32 rechazó la instalación del token de dispositivo."),
                )
            if not set_ok:
                active["mutated"].remove("token")
                _write_secret_journal(path, active)
                error = RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El ESP32 rechazó la instalación del token de dispositivo.")
                if active["mutated"]:
                    _fail_after_rollback(client, path, active, error)
                if os.path.isfile(path):
                    os.remove(path)
                raise error
            if client.verify_device_token(new_token_to_write) is not True:
                _fail_after_rollback(
                    client, path, active,
                    RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que el token no coincide tras la escritura."),
                )

        db_registered = False
        if sync_db:
            if journal is not None:
                journal.setdefault("intended", {})
                journal["intended"]["pop"] = target_pop
                journal["intended"]["code"] = serial_no
                if final_token_for_db:
                    journal["intended"]["token"] = final_token_for_db
                journal["stage"] = "db_pending"
                _write_secret_journal(journal_path, journal)
            try:
                _ensure_repo_on_path()
                from Conexión.conexion import register_dispositivo_fabrica
                register_dispositivo_fabrica(serial_no, mac, target_pop, final_token_for_db, force=force)
                db_registered = True
            except Exception as db_err:
                if journal is not None and journal.get("mutated"):
                    _fail_after_rollback(client, journal_path, journal, db_err)
                raise
            if journal is not None:
                journal["stage"] = "db_committed"
                _write_secret_journal(journal_path, journal)

        if journal_path and os.path.isfile(journal_path):
            os.remove(journal_path)

        mutated = journal.get("mutated") if journal else []
        if not mutated:
            action_taken = "identidad_existente_conservada"
        elif replace_pop:
            action_taken = "nueva_identidad_instalada"
        else:
            action_taken = "identidad_actualizada"

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
            "device_token": final_token_for_db,
            "label_file": out_filename,
            "verified": True,
            "db_registered": db_registered,
            "identity_conserved": not mutated,
        }
    finally:
        client.close()


def coordinate_placeholder_migration(
    port: str | None = None,
    out_dir: str = "docs/soporte/etiquetas",
    sync_db: bool = True,
    state_dir: str | None = None,
) -> dict:
    """Actualiza un placeholder de forma coordinada: base primero, NVS después, con reversión verificada.

    No rota PoP ni token y no borra al usuario. IDENT? por sí solo no hace este cambio.
    """
    _ensure_repo_on_path()
    from tools.migrate_identities import apply_migrations, revert_code_migration

    selected_port = port
    if not selected_port:
        detected = Esp32SerialClient.detect_ports()
        if not detected:
            raise RuntimeError("No se detectó ningún ESP32 conectado.")
        selected_port = detected[0]

    state_directory = provision_state_dir(out_dir, state_dir)
    client = Esp32SerialClient(selected_port)
    client.connect()
    try:
        ident = client.get_identity()
        mac = normalize_mac(ident["mac"])
        current_code = (ident.get("code") or "").strip().upper()
        suggested = _canonical_from_mac(mac)
        ble_name = ident.get("ble_name", derive_ble_name(mac))
        existing_pop = (ident.get("pop") or "").strip().upper()
        has_pop = bool(ident.get("has_pop")) and len(existing_pop) == 8

        if current_code == suggested and client.verify_code(suggested) is True:
            return {
                "status": "success",
                "action": "codigo_ya_canonico",
                "mac": mac,
                "serial": suggested,
                "verified": True,
                "db_registered": False,
                "identity_mutated": False,
                "label_file": None,
            }

        if current_code and not _placeholder_code(current_code) and current_code != suggested:
            raise RuntimeError(
                "La torre ya tiene un código activo distinto del sugerido por su MAC. "
                "Consultar IDENT no lo cambia. Hace falta una decisión explícita de taller."
            )

        db_mutated = False
        if sync_db:
            migration = apply_migrations(dry_run=False, only_mac=mac)
            if migration["requires_workshop"]:
                raise RuntimeError(
                    "Migración de base detenida por conflicto o MAC inutilizable. El hardware no se modificó."
                )
            db_mutated = migration["migrated"] > 0

        path, journal = _begin_journal(
            state_directory,
            mac,
            "migrate",
            {"pop": existing_pop if has_pop else None, "code": current_code or None, "token": None},
        )
        journal["stage"] = "db_committed" if db_mutated else "hardware_pending"
        journal["target_code"] = suggested
        journal["db_mutated"] = db_mutated
        _note_mutation(path, journal, "code")

        try:
            client.set_code(suggested)
            if client.verify_code(suggested) is not True:
                raise RuntimeError("FALLO CRÍTICO DE VERIFICACIÓN: El hardware reporta que el código no coincide.")
        except Exception as exc:
            after = current_code
            try:
                after = (client.get_identity().get("code") or "").strip().upper()
            except Exception:
                after = ""
            if db_mutated and after == current_code:
                reverted = revert_code_migration(mac, current_code, suggested)
                if reverted.get("reverted") or reverted.get("reason") == "ya_estaba_en_codigo_anterior":
                    if os.path.isfile(path):
                        os.remove(path)
                    raise RuntimeError(
                        f"{exc} El hardware sigue en el código anterior y la base fue revertida."
                    ) from None
            journal["stage"] = "repair_required"
            journal["identity_conserved"] = False
            _write_secret_journal(path, journal)
            raise RuntimeError(f"{exc} {_repair_text(['code'])}") from None

        if os.path.isfile(path):
            os.remove(path)

        label_file = None
        if has_pop:
            label_file = os.path.join(out_dir, f"{ble_name}_etiqueta.svg")
            save_secure_label(label_file, generate_svg_label(mac, ble_name, existing_pop, suggested))

        return {
            "status": "success",
            "action": "codigo_migrado",
            "mac": mac,
            "serial": suggested,
            "verified": True,
            "db_registered": db_mutated,
            "identity_mutated": True,
            "label_file": label_file,
            "pop_conserved": has_pop,
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

    mig_parser = subparsers.add_parser("migrate-code", help="Migrar un placeholder coordinando base, NVS y etiqueta sin rotar PoP ni token")
    mig_parser.add_argument("--port", help="Puerto serial del ESP32")
    mig_parser.add_argument("--no-db", action="store_true", help="Cambiar solo la NVS; no escribe la base")
    mig_parser.add_argument("--out", default="docs/soporte/etiquetas", help="Carpeta destino para la etiqueta SVG")

    rec_parser = subparsers.add_parser("recover", help="Restaurar una mutación de aprovisionamiento interrumpida y verificarla")
    rec_parser.add_argument("--port", help="Puerto serial del ESP32")
    rec_parser.add_argument("--out", default="docs/soporte/etiquetas", help="Carpeta donde está el estado de recuperación")

    for p in [prov_parser, ver_parser, read_parser, gen_parser, mig_parser, rec_parser]:
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
            print(f"Verificación:    Readback de los campos escritos")
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
            print(f"Código almacenado: {ident.get('code') or '(vacío)'}")
            print(f"Código válido:   {'Sí' if ident.get('code_valid') else 'No'}")
            print(f"Sugerido por MAC: {ident.get('suggested_code') or '(no reportado)'}")
            print(f"Identidad mutada: {'Sí' if ident.get('identity_mutated') else 'No'}")
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
    elif args.command == "migrate-code":
        try:
            res = coordinate_placeholder_migration(
                port=args.port,
                out_dir=args.out,
                sync_db=not args.no_db,
            )
            print("=" * 60)
            print("MIGRACIÓN DE CÓDIGO")
            print("=" * 60)
            print(f"MAC:             {res['mac']}")
            print(f"Código:          {res['serial']}")
            print(f"Acción:          {res['action']}")
            print(f"Verificación:    {'Readback coincidente' if res['verified'] else 'No verificada'}")
            print(f"Base de Datos:   {'Código actualizado' if res['db_registered'] else 'Sin cambio de fila en esta ejecución'}")
            print(f"Etiqueta:        {res['label_file'] or 'No reimpresa (sin PoP previa verificada)'}")
            print("=" * 60)
            if not res["verified"]:
                sys.exit(1)
        except Exception as exc:
            print(f"ERROR DE MIGRACIÓN: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "recover":
        try:
            ports = [args.port] if args.port else Esp32SerialClient.detect_ports()
            if not ports:
                raise RuntimeError("No se detectó ningún ESP32 conectado.")
            client = Esp32SerialClient(ports[0])
            client.connect()
            try:
                ident = client.get_identity()
                mac = normalize_mac(ident["mac"])
                state_directory = provision_state_dir(args.out)
                res = recover_open_provision(client, state_directory, mac)
            finally:
                client.close()
            print(f"Recuperación: {res['status']}")
            print(f"Identidad conservada: {'sí' if res['identity_conserved'] else 'no'}")
            if res["status"] == "repair_required" or not res["identity_conserved"]:
                print(_repair_text(res.get("unrestored") or []), file=sys.stderr)
                sys.exit(1)
        except Exception as exc:
            print(f"ERROR DE RECUPERACIÓN: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
