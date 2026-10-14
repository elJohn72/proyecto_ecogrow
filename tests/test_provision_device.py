"""Pruebas unitarias para la herramienta de aprovisionamiento de fábrica y vinculación de identidad EcoGrow 2.0."""
import json
import os
import stat
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.provision_device import (
    BASE32_CHARSET,
    Esp32SerialClient,
    _journal_path,
    _write_secret_journal,
    build_provisioning_payload,
    coordinate_placeholder_migration,
    derive_ble_name,
    extract_pop_from_svg,
    generate_offline_label,
    generate_qr_svg_elements,
    generate_secure_pop,
    generate_svg_label,
    normalize_mac,
    parse_qr_or_pin,
    provision_hardware_device,
    provision_state_dir,
    recover_open_provision,
    save_secure_label,
    verify_hardware_device,
)


class TestProvisionDeviceCryptoAndPayload(unittest.TestCase):
    """Pruebas para generación criptográfica, payloads y parsing."""

    def test_generate_secure_pop_length_and_charset(self):
        pop1 = generate_secure_pop(8)
        pop2 = generate_secure_pop(8)
        self.assertEqual(len(pop1), 8)
        self.assertEqual(len(pop2), 8)
        self.assertNotEqual(pop1, pop2)
        for char in pop1:
            self.assertIn(char, BASE32_CHARSET)
        for char in pop2:
            self.assertIn(char, BASE32_CHARSET)

    def test_normalize_mac_valid_formats(self):
        self.assertEqual(normalize_mac("44:1D:64:F8:70:C4"), "44:1D:64:F8:70:C4")
        self.assertEqual(normalize_mac("44-1d-64-f8-70-c4"), "44:1D:64:F8:70:C4")
        self.assertEqual(normalize_mac("441d64f870c4"), "44:1D:64:F8:70:C4")

    def test_normalize_mac_invalid(self):
        with self.assertRaises(ValueError):
            normalize_mac("INVALID_MAC")
        with self.assertRaises(ValueError):
            normalize_mac("44:1D:64:F8")

    def test_derive_ble_name(self):
        name = derive_ble_name("44:1D:64:F8:70:C4")
        self.assertEqual(name, "PROV_EcoGrow_70C4")

    def test_build_provisioning_payload(self):
        payload = build_provisioning_payload("PROV_EcoGrow_70C4", "A7K9M2PX")
        self.assertEqual(payload["ver"], "v1")
        self.assertEqual(payload["name"], "PROV_EcoGrow_70C4")
        self.assertEqual(payload["pop"], "A7K9M2PX")
        self.assertEqual(payload["transport"], "ble")

    def test_parse_qr_or_pin(self):
        # Desde JSON completo
        json_qr = '{"ver":"v1","name":"PROV_EcoGrow_70C4","pop":"9XZ24KPM","transport":"ble"}'
        self.assertEqual(parse_qr_or_pin(json_qr), "9XZ24KPM")
        # Desde PIN plano con espacios/minúsculas
        self.assertEqual(parse_qr_or_pin("  9xz24kpm  "), "9XZ24KPM")


class TestLabelAndQrGeneration(unittest.TestCase):
    """Pruebas para la generación del código QR matricial y etiqueta SVG con permisos seguros."""

    def test_generate_qr_svg_elements(self):
        payload = '{"ver":"v1","name":"PROV_EcoGrow_70C4","pop":"A7K9M2PX","transport":"ble"}'
        matrix_size, qr_svg = generate_qr_svg_elements(payload, size=120.0)
        self.assertGreater(matrix_size, 20)
        self.assertIn("<rect", qr_svg)
        self.assertIn('fill="#000000"', qr_svg)

    def test_generate_svg_label_contains_elements(self):
        mac = "44:1D:64:F8:70:C4"
        ble_name = "PROV_EcoGrow_70C4"
        pop = "A7K9M2PX"
        serial = "EG-TORRE-F870C4"
        svg = generate_svg_label(mac, ble_name, pop, serial)

        self.assertIn(mac, svg)
        self.assertIn(ble_name, svg)
        self.assertIn(pop, svg)
        self.assertIn(serial, svg)
        self.assertIn("ECOGROW-QR-PAYLOAD:", svg)
        self.assertIn("class=\"pin-text\"", svg)

        # Extracción inversa desde SVG
        extracted = extract_pop_from_svg(svg)
        self.assertEqual(extracted, pop)

    def test_save_secure_label_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            label_file = os.path.join(tmpdir, "test_label.svg")
            save_secure_label(label_file, "<svg></svg>")
            self.assertTrue(os.path.isfile(label_file))

            mode = stat.S_IMODE(os.stat(label_file).st_mode)
            # Debe tener permisos 0600 (lectura y escritura solo para propietario)
            self.assertEqual(mode, 0o600)

    def test_generate_offline_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = generate_offline_label(
                mac="44:1D:64:F8:70:C4",
                pop="TESTPOP8",
                out_dir=tmpdir,
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["pop"], "TESTPOP8")
            self.assertEqual(res["ble_name"], "PROV_EcoGrow_70C4")
            self.assertTrue(os.path.isfile(res["label_file"]))

            with open(res["label_file"], "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("TESTPOP8", content)
            self.assertIn("PROV_EcoGrow_70C4", content)


class TestSerialProtocolAndHardwareProvisioning(unittest.TestCase):
    """Pruebas del protocolo serie y flujos de aprovisionamiento en hardware."""

    def setUp(self):
        patcher_code = patch("tools.provision_device.Esp32SerialClient.set_code", return_value="CODE_OK")
        patcher_vcode = patch("tools.provision_device.Esp32SerialClient.verify_code", return_value=True)
        patcher_token = patch("tools.provision_device.Esp32SerialClient.set_device_token", return_value=True)
        self.patcher_vtoken = patch("tools.provision_device.Esp32SerialClient.verify_device_token", return_value=True)
        self.mock_set_code = patcher_code.start()
        self.mock_verify_code = patcher_vcode.start()
        self.mock_set_token = patcher_token.start()
        self.mock_verify_token = self.patcher_vtoken.start()
        self.addCleanup(patcher_code.stop)
        self.addCleanup(patcher_vcode.stop)
        self.addCleanup(patcher_token.stop)
        self.addCleanup(self.patcher_vtoken.stop)

    def test_esp32_serial_client_communication(self):
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.side_effect = [
            b"BOOT LOG\r\n",
            b'ECOGROW:IDENT:{"mac":"44:1D:64:F8:70:C4","ble_name":"PROV_EcoGrow_70C4","pop":"A7K9M2PX","has_pop":true}\r\n',
        ]

        client = Esp32SerialClient(port="/dev/mock_esp32", timeout=1.0)
        client.ser = mock_serial

        ident = client.get_identity()
        self.assertEqual(ident["mac"], "44:1D:64:F8:70:C4")
        self.assertEqual(ident["ble_name"], "PROV_EcoGrow_70C4")
        self.assertEqual(ident["pop"], "A7K9M2PX")
        self.assertTrue(ident["has_pop"])

    def test_esp32_serial_client_set_and_verify(self):
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.side_effect = [
            b'ECOGROW:SET_POP_OK:{"pop":"NEWPOP22"}\r\n',
            b'ECOGROW:VERIFY:{"match":true}\r\n',
            b'ECOGROW:VERIFY:{"match":false}\r\n',
            b'ECOGROW:VERIFY_TOKEN:{"match":true}\r\n',
            b'ECOGROW:VERIFY_TOKEN:{"match":false}\r\n',
        ]

        client = Esp32SerialClient(port="/dev/mock_esp32", timeout=1.0)
        client.ser = mock_serial

        # Set pop
        res_pop = client.set_pop("NEWPOP22")
        self.assertEqual(res_pop, "NEWPOP22")

        # Verify ok
        self.assertTrue(client.verify_pop("NEWPOP22"))

        # Verify mismatch
        self.assertFalse(client.verify_pop("WRONGPOP"))

        # Verify device token (challenge readback) - unstop mock for this test
        self.patcher_vtoken.stop()
        try:
            self.assertTrue(client.verify_device_token("CORRECT_SECRET_TOKEN"))
            self.assertFalse(client.verify_device_token("WRONG_SECRET_TOKEN"))
        finally:
            self.patcher_vtoken.start()

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_provision_hardware_conserves_existing_pop_by_default(
        self, mock_close, mock_verify, mock_set, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "EXISTING",
                "has_pop": True,
                "code": "EG-TORRE-F870C4",
                "has_token": True,
            }
            mock_verify.return_value = True
            mock_db_disp = {
                "estado": "fabrica",
                "device_token": "EXISTING_DB_TOKEN_1234",
            }

            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=mock_db_disp), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True):
                res = provision_hardware_device(
                    port="/dev/ttyUSB0",
                    force=False,
                    out_dir=tmpdir,
                )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["action"], "identidad_existente_conservada")
            self.assertTrue(res["identity_conserved"])
            self.assertEqual(res["pop"], "EXISTING")
            mock_set.assert_not_called()
            self.mock_set_code.assert_not_called()
            self.mock_set_token.assert_not_called()
            mock_verify.assert_called_once_with("EXISTING")
            self.assertTrue(os.path.isfile(res["label_file"]))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_provision_hardware_installs_new_pop_when_missing_or_forced(
        self, mock_close, mock_verify, mock_set, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Caso sin PoP previa
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "",
                "has_pop": False,
            }
            mock_set.return_value = "BRANDNEW"
            mock_verify.return_value = True

            res = provision_hardware_device(
                port="/dev/ttyUSB0",
                desired_pop="BRANDNEW",
                force=False,
                out_dir=tmpdir,
            )

            self.assertEqual(res["action"], "nueva_identidad_instalada")
            self.assertEqual(res["pop"], "BRANDNEW")
            mock_set.assert_called_once_with("BRANDNEW")
            mock_verify.assert_called_once_with("BRANDNEW")
            self.assertTrue(os.path.isfile(res["label_file"]))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_provision_hardware_aborts_if_verification_fails(
        self, mock_close, mock_verify, mock_set, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "",
                "has_pop": False,
            }
            mock_set.return_value = "TESTFAILS"
            # Simular fallo de verificación en hardware
            mock_verify.return_value = False

            with self.assertRaises(RuntimeError) as ctx:
                provision_hardware_device(
                    port="/dev/ttyUSB0",
                    desired_pop="TESTFAILS",
                    out_dir=tmpdir,
                )

            self.assertIn("FALLO CRÍTICO DE VERIFICACIÓN", str(ctx.exception))
            self.assertNotIn("TESTFAILS", str(ctx.exception))
            self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_verify_hardware_device_with_label_file(
        self, mock_close, mock_verify, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            label_file = os.path.join(tmpdir, "PROV_EcoGrow_70C4_etiqueta.svg")
            svg = generate_svg_label("44:1D:64:F8:70:C4", "PROV_EcoGrow_70C4", "MATCH999", "SERIAL1")
            save_secure_label(label_file, svg)

            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "MATCH999",
                "has_pop": True,
            }
            mock_verify.return_value = True

            res = verify_hardware_device(port="/dev/ttyUSB0", label_path=label_file)
            self.assertTrue(res["match"])
            self.assertEqual(res["expected_pop"], "MATCH999")
            mock_verify.assert_called_once_with("MATCH999")

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.set_code")
    @patch("tools.provision_device.Esp32SerialClient.verify_code", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.set_device_token", return_value=False)
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_provision_fails_if_set_device_token_rejected(
        self, mock_close, mock_set_token, mock_ver_code, mock_set_code, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "",
                "has_pop": False,
                "has_token": False,
            }
            mock_set_pop.return_value = "TESTPOP1"
            mock_verify.return_value = True

            with self.assertRaises(RuntimeError) as ctx:
                provision_hardware_device(
                    port="/dev/ttyUSB0",
                    desired_pop="TESTPOP1",
                    out_dir=tmpdir,
                    sync_db=False,
                )

            self.assertIn("rechazó la instalación del token de dispositivo", str(ctx.exception))
            self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.set_code")
    @patch("tools.provision_device.Esp32SerialClient.verify_code", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.set_device_token")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_second_provisioning_preserves_token_without_rotate(
        self, mock_close, mock_set_token, mock_ver_code, mock_set_code, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": True,
            }
            mock_verify.return_value = True

            mock_db_disp = {
                "codigo_dispositivo": "EG-TORRE-F870C4",
                "estado": "fabrica",
                "device_token": "EXISTING_DB_TOKEN_1234",
            }
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=mock_db_disp), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True) as mock_reg_db:

                res = provision_hardware_device(
                    port="/dev/ttyUSB0",
                    desired_pop="TESTPOP1",
                    out_dir=tmpdir,
                    rotate_token=False,
                    sync_db=True,
                )

                # No debe haber llamado a set_device_token porque se conserva el existente
                mock_set_token.assert_not_called()
                self.assertEqual(res["device_token"], "EXISTING_DB_TOKEN_1234")
                self.assertTrue(res["db_registered"])
                mock_reg_db.assert_called_once_with(
                    "EG-TORRE-F870C4", "44:1D:64:F8:70:C4", "TESTPOP1", "EXISTING_DB_TOKEN_1234", force=False
                )

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.set_code")
    @patch("tools.provision_device.Esp32SerialClient.verify_code", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.set_device_token", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_second_provisioning_rotates_token_when_requested(
        self, mock_close, mock_set_token, mock_ver_code, mock_set_code, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": True,
            }
            mock_verify.return_value = True

            mock_db_disp = {
                "codigo_dispositivo": "EG-TORRE-F870C4",
                "estado": "fabrica",
                "device_token": "EXISTING_DB_TOKEN_1234",
            }
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=mock_db_disp), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True):

                res = provision_hardware_device(
                    port="/dev/ttyUSB0",
                    desired_pop="TESTPOP1",
                    out_dir=tmpdir,
                    rotate_token=True,
                    sync_db=True,
                )

                # Debe haber rotado llamando a set_device_token
                mock_set_token.assert_called_once()
                self.assertNotEqual(res["device_token"], "EXISTING_DB_TOKEN_1234")

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.set_code")
    @patch("tools.provision_device.Esp32SerialClient.verify_code", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.set_device_token", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_database_failure_aborts_provisioning_and_does_not_create_label(
        self, mock_close, mock_set_token, mock_ver_code, mock_set_code, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": False,
            }
            mock_verify.return_value = True

            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=None), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True, side_effect=RuntimeError("MariaDB connection lost")):

                with self.assertRaises(RuntimeError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        desired_pop="TESTPOP1",
                        out_dir=tmpdir,
                        sync_db=True,
                    )

                self.assertIn("MariaDB connection lost", str(ctx.exception))
                self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_preflight_aborts_without_mutating_hardware_when_claimed(
        self, mock_close, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "OLDPOP11",
                "has_pop": True,
                "has_token": True,
            }
            claimed_disp = {
                "codigo_dispositivo": "EG-TORRE-F870C4",
                "estado": "reclamada",
                "device_token": "TOK1",
            }
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=claimed_disp):
                with self.assertRaises(ValueError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        desired_pop="NEWPOP22",
                        force=False,
                        out_dir=tmpdir,
                        sync_db=True,
                    )

                self.assertIn("ya fue reclamado por un usuario", str(ctx.exception))
                # Hardware NO debe haber sido mutado
                mock_set_pop.assert_not_called()
                self.mock_set_code.assert_not_called()
                self.mock_set_token.assert_not_called()
                self.assertEqual(len(os.listdir(tmpdir)), 0)

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_token_rotation_rollback_on_database_failure(
        self, mock_close, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": True,
            }
            mock_verify.return_value = True

            existing_disp = {
                "codigo_dispositivo": "EG-TORRE-F870C4",
                "estado": "fabrica",
                "device_token": "VERIFIED_OLD_TOKEN_999",
            }
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=existing_disp), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True, side_effect=RuntimeError("DB write failure")):

                with self.assertRaises(RuntimeError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        rotate_token=True,
                        sync_db=True,
                        out_dir=tmpdir,
                    )

                self.assertIn("DB write failure", str(ctx.exception))
                # Debe haberse llamado a set_device_token con nuevo token y luego con rollback al token previo
                calls = self.mock_set_token.call_args_list
                self.assertGreaterEqual(len(calls), 2)
                # La última llamada a set_device_token debe restaurar el token anterior
                last_call_token = calls[-1][0][0]
                self.assertEqual(last_call_token, "VERIFIED_OLD_TOKEN_999")

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_offline_mode_preserves_token_without_rotate(
        self, mock_close, mock_verify, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": True,
            }
            mock_verify.return_value = True

            res = provision_hardware_device(
                port="/dev/ttyUSB0",
                sync_db=False,
                rotate_token=False,
                out_dir=tmpdir,
            )

            self.assertEqual(res["status"], "success")
            self.assertIsNone(res["device_token"])
            self.mock_set_token.assert_not_called()

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_token_desync_detected_and_aborts_without_mutation(
        self, mock_close, mock_set_pop, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "TESTPOP1",
                "has_pop": True,
                "has_token": True,
            }
            # Simular desincronización: hardware responde match=False ante el token de la DB
            self.mock_verify_token.return_value = False

            existing_disp = {
                "codigo_dispositivo": "EG-TORRE-F870C4",
                "estado": "fabrica",
                "device_token": "DB_TOKEN_THAT_DOES_NOT_MATCH_HW",
            }
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=existing_disp):
                with self.assertRaises(RuntimeError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        sync_db=True,
                        force=False,
                        rotate_token=False,
                        out_dir=tmpdir,
                    )

                self.assertIn("DESINCRONIZACIÓN DE TOKEN", str(ctx.exception))
                mock_set_pop.assert_not_called()
                self.mock_set_token.assert_not_called()

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_database_failure_restores_pop_and_reports_failed_token_rollback(
        self, mock_close, mock_verify_pop, mock_set_pop, mock_ident, mock_connect
    ):
        state = {"pop": "OLDPOP11", "token": "VERIFIED_OLD_TOKEN_999"}

        def set_pop(pop):
            state["pop"] = pop
            return pop

        def verify_pop(pop):
            return state["pop"] == pop

        def set_token(token):
            if token == "VERIFIED_OLD_TOKEN_999":
                return False
            state["token"] = token
            return True

        def verify_token(token):
            return token == state["token"]

        mock_set_pop.side_effect = set_pop
        mock_verify_pop.side_effect = verify_pop
        self.mock_set_token.side_effect = set_token
        self.mock_verify_token.side_effect = verify_token
        mock_ident.return_value = {
            "mac": "44:1D:64:F8:70:C4",
            "ble_name": "PROV_EcoGrow_70C4",
            "pop": "OLDPOP11",
            "has_pop": True,
            "code": "EG-TORRE-F870C4",
            "has_token": True,
        }
        existing = {
            "estado": "fabrica",
            "device_token": "VERIFIED_OLD_TOKEN_999",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=existing), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True, side_effect=RuntimeError("DB write failure")):
                with self.assertRaises(RuntimeError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        desired_pop="NEWPOP22",
                        rotate_token=True,
                        sync_db=True,
                        out_dir=tmpdir,
                    )
            message = str(ctx.exception)
            self.assertIn("DB write failure", message)
            self.assertIn("Reparación requerida", message)
            self.assertIn("no quedó conservada", message)
            self.assertNotIn("NEWPOP22", message)
            self.assertNotIn("VERIFIED_OLD_TOKEN_999", message)
            self.assertEqual(state["pop"], "OLDPOP11")
            self.assertEqual(mock_set_pop.call_args_list[-1].args[0], "OLDPOP11")
            self.assertIn("OLDPOP11", [call.args[0] for call in mock_verify_pop.call_args_list])
            self.assertEqual(self.mock_set_token.call_args_list[-1].args[0], "VERIFIED_OLD_TOKEN_999")
            self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop", return_value=True)
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_token_readback_failure_restores_previous_token(
        self, mock_close, mock_verify_pop, mock_set_pop, mock_ident, mock_connect
    ):
        def verify_token(token):
            return token == "VERIFIED_OLD_TOKEN_999"

        self.mock_verify_token.side_effect = verify_token
        self.mock_set_token.side_effect = lambda token: True
        mock_ident.return_value = {
            "mac": "44:1D:64:F8:70:C4",
            "ble_name": "PROV_EcoGrow_70C4",
            "pop": "OLDPOP11",
            "has_pop": True,
            "code": "EG-TORRE-F870C4",
            "has_token": True,
        }
        existing = {"estado": "fabrica", "device_token": "VERIFIED_OLD_TOKEN_999"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True, return_value=existing), \
                 patch("Conexión.conexion.register_dispositivo_fabrica", create=True) as mock_reg:
                with self.assertRaises(RuntimeError) as ctx:
                    provision_hardware_device(
                        port="/dev/ttyUSB0",
                        rotate_token=True,
                        sync_db=True,
                        out_dir=tmpdir,
                    )
            self.assertIn("token no coincide tras la escritura", str(ctx.exception))
            self.assertEqual(self.mock_set_token.call_args_list[-1].args[0], "VERIFIED_OLD_TOKEN_999")
            self.assertGreaterEqual(len(self.mock_verify_token.call_args_list), 2)
            mock_reg.assert_not_called()
            mock_set_pop.assert_not_called()
            self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    def test_interrupted_journal_restores_and_verifies_pop(self):
        class Client:
            def __init__(self):
                self.pop = "NEWPOP22"

            def set_pop(self, pop):
                self.pop = pop
                return pop

            def verify_pop(self, pop):
                return self.pop == pop

            def set_code(self, code):
                return code

            def verify_code(self, code):
                return True

            def set_device_token(self, token):
                return True

            def verify_device_token(self, token):
                return True

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = provision_state_dir(tmpdir)
            mac = "44:1D:64:F8:70:C4"
            path = _journal_path(state_dir, mac, "provision")
            _write_secret_journal(path, {
                "version": 1,
                "mac": mac,
                "stage": "mutating",
                "previous": {"pop": "OLDPOP11", "code": "EG-TORRE-F870C4", "token": None},
                "mutated": ["pop"],
                "identity_conserved": False,
            })
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            client = Client()
            result = recover_open_provision(client, state_dir, mac)
            self.assertEqual(result["status"], "restored")
            self.assertTrue(result["identity_conserved"])
            self.assertEqual(client.pop, "OLDPOP11")
            self.assertFalse(os.path.isfile(path))

    def test_committed_token_is_not_rolled_back(self):
        class Client:
            def __init__(self):
                self.token = "NEW_TOKEN_VALUE_123456"
                self.writes = []

            def verify_device_token(self, token):
                return token == self.token

            def set_device_token(self, token):
                self.writes.append(token)
                self.token = token
                return True

            def verify_pop(self, pop):
                return True

            def verify_code(self, code):
                return True

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = provision_state_dir(tmpdir)
            mac = "44:1D:64:F8:70:C4"
            path = _journal_path(state_dir, mac, "provision")
            _write_secret_journal(path, {
                "version": 1,
                "mac": mac,
                "stage": "db_pending",
                "previous": {"token": "OLD_TOKEN_VALUE_123456"},
                "intended": {"token": "NEW_TOKEN_VALUE_123456"},
                "mutated": ["token"],
                "identity_conserved": False,
            })
            client = Client()
            result = recover_open_provision(
                client, state_dir, mac,
                cloud={"token_is_intended": True, "token_is_previous": False},
            )
            self.assertEqual(result["status"], "reconciled")
            self.assertTrue(result["credentials_agree"])
            self.assertFalse(result["identity_conserved"])
            self.assertEqual(client.writes, [])
            self.assertFalse(os.path.isfile(path))

            _write_secret_journal(path, {
                "version": 1,
                "mac": mac,
                "stage": "db_committed",
                "previous": {"token": "OLD_TOKEN_VALUE_123456"},
                "intended": {"token": "NEW_TOKEN_VALUE_123456"},
                "mutated": ["token"],
            })
            client.token = "OLD_TOKEN_VALUE_123456"
            diverged = recover_open_provision(
                client, state_dir, mac,
                cloud={"token_is_intended": True, "token_is_previous": False},
            )
            self.assertEqual(diverged["status"], "repair_required")
            self.assertFalse(diverged["identity_conserved"])
            self.assertFalse(diverged["credentials_agree"])
            self.assertEqual(client.writes, [])
            self.assertEqual(client.token, "OLD_TOKEN_VALUE_123456")

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_coordinate_migration_keeps_pop_and_token(
        self, mock_close, mock_set_pop, mock_ident, mock_connect
    ):
        mock_ident.return_value = {
            "mac": "44:1D:64:F8:70:C4",
            "ble_name": "PROV_EcoGrow_70C4",
            "pop": "KEEPOP11",
            "has_pop": True,
            "code": "TORRE-001",
            "has_token": True,
        }
        migration = {"migrated": 1, "requires_workshop": 0, "skipped_canonical": 0, "details": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.migrate_identities.apply_migrations", return_value=migration):
                result = coordinate_placeholder_migration(port="/dev/ttyUSB0", out_dir=tmpdir, sync_db=True)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["verified"])
        self.assertEqual(result["serial"], "EG-TORRE-F870C4")
        mock_set_pop.assert_not_called()
        self.mock_set_token.assert_not_called()
        self.mock_set_code.assert_called_with("EG-TORRE-F870C4")

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_coordinate_reverts_database_when_hardware_keeps_old_code(
        self, mock_close, mock_ident, mock_connect
    ):
        mock_ident.return_value = {
            "mac": "44:1D:64:F8:70:C4",
            "ble_name": "PROV_EcoGrow_70C4",
            "pop": "KEEPOP11",
            "has_pop": True,
            "code": "TORRE-001",
        }
        self.mock_verify_code.return_value = False
        migration = {"migrated": 1, "requires_workshop": 0, "skipped_canonical": 0, "details": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.migrate_identities.apply_migrations", return_value=migration), \
                 patch("tools.migrate_identities.revert_code_migration", return_value={"reverted": True}) as revert:
                with self.assertRaises(RuntimeError) as ctx:
                    coordinate_placeholder_migration(port="/dev/ttyUSB0", out_dir=tmpdir, sync_db=True)
            self.assertIn("FALLO CRÍTICO DE VERIFICACIÓN", str(ctx.exception))
            self.assertIn("base fue revertida", str(ctx.exception))
            revert.assert_called_once()
            self.assertFalse(any(name.endswith(".svg") for name in os.listdir(tmpdir)))

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_coordinate_does_not_replace_an_active_code(
        self, mock_close, mock_ident, mock_connect
    ):
        mock_ident.return_value = {
            "mac": "44:1D:64:F8:70:C4",
            "ble_name": "PROV_EcoGrow_70C4",
            "pop": "KEEPOP11",
            "has_pop": True,
            "code": "EG-TORRE-ABCDEF",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.migrate_identities.apply_migrations") as migrate:
                with self.assertRaises(RuntimeError) as ctx:
                    coordinate_placeholder_migration(port="/dev/ttyUSB0", out_dir=tmpdir, sync_db=True)
        self.assertIn("código activo", str(ctx.exception))
        migrate.assert_not_called()
        self.mock_set_code.assert_not_called()
        self.mock_set_token.assert_not_called()


class TestSecretConfidentiality(unittest.TestCase):
    """Pruebas de confidencialidad: asegurar que la PoP no se filtra en logs, stdout ni excepciones."""

    def test_timeout_error_sanitizes_pop_in_exception(self):
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.return_value = b""  # Simular silencio del ESP32

        client = Esp32SerialClient(port="/dev/mock_esp32", timeout=0.1)
        client.ser = mock_serial

        secret_pop = "TOPSECR8"
        with self.assertRaises(TimeoutError) as ctx:
            client.set_pop(secret_pop)

        err_msg = str(ctx.exception)
        # Debe contener comando sanitizado con asteriscos y NO el secreto
        self.assertIn("ECOGROW:SET_POP:***", err_msg)
        self.assertNotIn(secret_pop, err_msg)

    @patch("tools.provision_device.Esp32SerialClient.connect")
    @patch("tools.provision_device.Esp32SerialClient.get_identity")
    @patch("tools.provision_device.Esp32SerialClient.set_pop")
    @patch("tools.provision_device.Esp32SerialClient.verify_pop")
    @patch("tools.provision_device.Esp32SerialClient.close")
    def test_readback_failure_does_not_contain_pop(
        self, mock_close, mock_verify, mock_set, mock_ident, mock_connect
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ident.return_value = {
                "mac": "44:1D:64:F8:70:C4",
                "ble_name": "PROV_EcoGrow_70C4",
                "pop": "",
                "has_pop": False,
            }
            mock_set.return_value = "SECRET88"
            mock_verify.return_value = False

            with self.assertRaises(RuntimeError) as ctx:
                provision_hardware_device(
                    port="/dev/ttyUSB0",
                    desired_pop="SECRET88",
                    out_dir=tmpdir,
                )

            err_msg = str(ctx.exception)
            self.assertIn("FALLO CRÍTICO DE VERIFICACIÓN", err_msg)
            self.assertNotIn("SECRET88", err_msg)

    def test_cli_generate_stdout_does_not_contain_pop_by_default(self):
        import io
        import sys
        from tools.provision_device import main

        with tempfile.TemporaryDirectory() as tmpdir:
            secret = "HIDDEN99"
            test_args = [
                "provision_device.py",
                "generate",
                "--mac", "44:1D:64:F8:70:C4",
                "--pop", secret,
                "--out", tmpdir,
            ]
            captured_stdout = io.StringIO()
            with patch.object(sys, "argv", test_args), patch("sys.stdout", captured_stdout):
                main()

            output = captured_stdout.getvalue()
            self.assertIn("CONFIDENCIAL", output)
            self.assertNotIn(secret, output)

    def test_timeout_error_sanitizes_device_token_in_exception(self):
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.return_value = b""  # Simular silencio del ESP32

        client = Esp32SerialClient(port="/dev/mock_esp32", timeout=0.1)
        client.ser = mock_serial

        secret_token = "TOPSECRETTOKEN123456"
        with self.assertRaises(TimeoutError) as ctx:
            client.set_device_token(secret_token)

        err_msg = str(ctx.exception)
        self.assertIn("ECOGROW:SET_DEVICE_TOKEN:***", err_msg)
        self.assertNotIn(secret_token, err_msg)

    def test_generate_offline_label_does_not_call_db_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("Conexión.conexion.register_dispositivo_fabrica", create=True) as mock_reg, \
                 patch("Conexión.conexion.fetch_dispositivo_by_codigo", create=True) as mock_fetch:

                res = generate_offline_label(
                    mac="44:1D:64:F8:70:C4",
                    pop="TESTPOP8",
                    out_dir=tmpdir,
                )
                self.assertEqual(res["status"], "success")
                mock_reg.assert_not_called()
                mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
