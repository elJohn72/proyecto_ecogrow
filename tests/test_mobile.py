"""PRUEBA fixtures only; every database operation is mocked."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from mysql.connector import Error

from app import app
from blueprints.mobile import _attempts
from services import mobile_service as service

USER = {"id_usuario": 1, "nombre": "PRUEBA", "mail": "prueba@example.invalid", "password": "PRUEBA"}
TOWER = {"id_torre": 7, "nombre": "PRUEBA", "codigo_unico": "PRUEBA-7", "estado": "activo"}


class MobileApiTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.user_mock = patch("services.mobile_service.user_by_id", return_value=USER).start()
        self.addCleanup(patch.stopall)
        _attempts.clear()

    def logged_in(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = "1"
            session["_fresh"] = True
            session["csrf_token"] = "PRUEBA-CSRF"
        return {"X-CSRF-Token": "PRUEBA-CSRF"}

    def test_session_anonymous_and_private_cache(self):
        response = self.client.get("/api/mobile/session")
        self.assertFalse(response.json["authenticated"])
        self.assertIsNone(response.json["user"])
        self.assertTrue(response.json["csrf_token"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_auth_error_is_json_without_redirect(self):
        response = self.client.get("/api/mobile/towers")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "auth_required")
        self.assertNotIn("Location", response.headers)

    def test_csrf_error_is_json(self):
        self.logged_in()
        response = self.client.post("/api/mobile/towers/7/pump", json={"state": "off"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "csrf_invalid")

    def test_login_rotates_csrf_and_clears_old_tower(self):
        csrf = self.client.get("/api/mobile/session").json["csrf_token"]
        with self.client.session_transaction() as session:
            session["torre_id"] = 999
        with patch.object(service, "authenticate", return_value=USER):
            response = self.client.post("/api/mobile/login", json={"mail": USER["mail"], "password": "PRUEBA"}, headers={"X-CSRF-Token": csrf})
        self.assertTrue(response.json["authenticated"])
        self.assertNotEqual(response.json["csrf_token"], csrf)
        self.assertNotIn("password", response.json["user"])
        with self.client.session_transaction() as session:
            self.assertNotIn("torre_id", session)

    def test_bad_login_credential_fields_and_json_arrays(self):
        headers = self.logged_in()
        for data in ([], None, {"mail": [], "password": "PRUEBA"}, {"mail": "PRUEBA", "password": {}}, {"state": "auto"}):
            response = self.client.post("/api/mobile/login", json=data, headers=headers)
            self.assertEqual(response.status_code, 400)

    def test_rate_limit(self):
        headers = self.logged_in()
        with patch.object(service, "authenticate", return_value=None):
            for _ in range(10):
                self.assertEqual(self.client.post("/api/mobile/login", json={"mail": USER["mail"], "password": "PRUEBA"}, headers=headers).status_code, 401)
            self.assertEqual(self.client.post("/api/mobile/login", json={"mail": USER["mail"], "password": "PRUEBA"}, headers=headers).status_code, 429)

    def test_logout_invalidates_session(self):
        response = self.client.post("/api/mobile/logout", json={}, headers=self.logged_in())
        self.assertFalse(response.json["authenticated"])
        self.assertEqual(self.client.get("/api/mobile/towers").status_code, 401)

    def test_database_failure_does_not_leak_details(self):
        self.logged_in()
        with patch.object(service, "list_towers", side_effect=Error("SECRET DATABASE HOST PRUEBA")):
            response = self.client.get("/api/mobile/towers")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.get_data(as_text=True))

    def test_pump_array_and_invalid_state(self):
        headers = self.logged_in()
        for data in ([], {"state": "auto"}, {"state": True}, {"state": {}}):
            response = self.client.post("/api/mobile/towers/7/pump", json=data, headers=headers)
            self.assertEqual(response.status_code, 400)

    def test_pump_returns_pending_not_confirmation(self):
        headers = self.logged_in()
        result = {"accepted": True, "desired": "off", "reported": None, "status": "pending", "message": "PRUEBA"}
        with patch.object(service, "command_pump", return_value=result) as command:
            response = self.client.post("/api/mobile/towers/7/pump", json={"state": "off"}, headers=headers)
        self.assertEqual(response.status_code, 202)
        self.assertIsNone(response.json["reported"])
        command.assert_called_once_with(7, 1, "off")

    def test_api_idor_denied(self):
        headers = self.logged_in()
        with patch.object(service, "_execute", return_value=None) as query:
            response = self.client.post("/api/mobile/towers/8/pump", json={"state": "off"}, headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(query.call_count, 1)
        self.assertIn("usuario_id = %s", query.call_args.args[0])
        self.assertEqual(query.call_args.args[1], (8, 1))


class MobileServiceTest(unittest.TestCase):
    def reading(self, level=70, age=0):
        return {"nivel_agua": level, "utc_reading_time": datetime.now(timezone.utc) - timedelta(seconds=age)}

    def pump_mocks(self, row):
        stack = []
        for name, result in (("owned_tower", TOWER), ("pump_row", {"modo": "manual"}), ("readings", [row]), ("configuration", {"nivel_minimo": 20})):
            mock = patch.object(service, name, return_value=result)
            stack.append(mock.start())
        self.addCleanup(patch.stopall)
        return stack

    def test_stale_future_missing_and_naive_times(self):
        for timestamp in (None, "bad", datetime.now(), datetime.now(timezone.utc) + timedelta(seconds=10), datetime.now(timezone.utc) - timedelta(seconds=121)):
            self.assertTrue(service.is_stale(timestamp))
        self.assertFalse(service.is_stale(datetime.now(timezone.utc)))

    def test_on_blocks_stale_without_mutation(self):
        self.pump_mocks(self.reading(age=121))
        with patch.object(service, "_execute") as execute:
            with self.assertRaises(service.MobileError) as caught:
                service.command_pump(7, 1, "on")
            self.assertEqual(caught.exception.code, "stale_reading")
            execute.assert_not_called()

    def test_on_blocks_invalid_low_and_nonfinite_level(self):
        self.pump_mocks(self.reading())
        with patch.object(service, "_execute") as execute:
            for level in (None, float("nan"), float("inf"), -1, 101, 0, 20):
                with patch.object(service, "readings", return_value=[self.reading(level)]):
                    with self.assertRaises(service.MobileError) as caught:
                        service.command_pump(7, 1, "on")
                    self.assertEqual(caught.exception.code, "unsafe_level")
            execute.assert_not_called()

    def test_on_requires_real_config(self):
        self.pump_mocks(self.reading())
        with patch.object(service, "configuration", return_value=None), patch.object(service, "_execute") as execute:
            with self.assertRaises(service.MobileError):
                service.command_pump(7, 1, "on")
            execute.assert_not_called()

    def test_on_with_valid_data_sets_only_desired(self):
        self.pump_mocks(self.reading())
        with patch.object(service, "_execute") as execute:
            result = service.command_pump(7, 1, "on")
        self.assertIsNone(result["reported"])
        self.assertEqual(result["status"], "pending")
        self.assertEqual(execute.call_args.args[1], ("encendida", 7))

    def test_off_allowed_without_fresh_sensor(self):
        self.pump_mocks({})
        with patch.object(service, "_execute") as execute:
            result = service.command_pump(7, 1, "off")
        self.assertEqual(result["desired"], "off")
        execute.assert_called_once()

    def test_no_invented_tds_volume_or_nonfinite_sensors(self):
        result = service.sensors({"ec": 1.8, "ph": float("nan"), "nivel_agua": 70})
        self.assertEqual(result["ec_ms_cm"], 1.8)
        self.assertIsNone(result["ph"])
        self.assertIsNone(result["tds_ppm"])
        self.assertIsNone(result["litros"])

    def test_irrigation_validation_before_write(self):
        with patch.object(service, "owned_tower", return_value=TOWER), patch.object(service, "irrigation_row", return_value={"estrategia": "PRUEBA"}), patch.object(service, "_execute") as execute:
            for data in ({}, {"enabled": True, "on_minutes": True, "off_minutes": 5}, {"enabled": "yes", "on_minutes": 1, "off_minutes": 5}, {"enabled": True, "on_minutes": 0, "off_minutes": 5}, {"enabled": True, "on_minutes": 1, "off_minutes": 1441}):
                with self.assertRaises(service.MobileError):
                    service.save_irrigation(7, 1, data)
            execute.assert_not_called()

    def test_queries_do_not_initialize_schema(self):
        with patch.object(service, "_execute", return_value=[]) as execute:
            service.list_towers(1)
            service.readings(7)
        for call in execute.call_args_list:
            self.assertTrue(call.args[0].lstrip().startswith("SELECT"))

    def test_mysql_age_normalizes_reading_to_utc(self):
        with patch.object(service, "_execute", return_value=[{"fecha_registro": datetime.now(), "age_seconds": 5}]):
            row = service.readings(7)[0]
        self.assertIsNotNone(row["utc_reading_time"].tzinfo)
        self.assertFalse(service.is_stale(row["utc_reading_time"]))


if __name__ == "__main__":
    unittest.main()
