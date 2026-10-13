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
    build_provisioning_payload,
    derive_ble_name,
    extract_pop_from_svg,
    generate_offline_label,
    generate_qr_svg_elements,
    generate_secure_pop,
    generate_svg_label,
    normalize_mac,
    parse_qr_or_pin,
    provision_hardware_device,
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
            }
            mock_verify.return_value = True

            res = provision_hardware_device(
                port="/dev/ttyUSB0",
                force=False,
                out_dir=tmpdir,
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["action"], "identidad_existente_conservada")
            self.assertEqual(res["pop"], "EXISTING")
            mock_set.assert_not_called()
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
            # Verificar que no se generó etiqueta si falló la verificación
            files = os.listdir(tmpdir)
            self.assertEqual(len(files), 0)

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


if __name__ == "__main__":
    unittest.main()
