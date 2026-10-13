"""PRUEBA fixtures only; every database operation is mocked."""
import time
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

    def test_command_mode_and_recipe_endpoints(self):
        headers = self.logged_in()
        with patch.object(service, "owned_tower", return_value=TOWER), patch.object(service, "_execute"), patch.object(service, "_execute_transaction"):
            res_mode = self.client.post("/api/mobile/towers/7/mode", json={"mode": "auto"}, headers=headers)
            self.assertEqual(res_mode.status_code, 202)
            self.assertEqual(res_mode.json["desired"], "AUTO")

            res_recipe = self.client.post("/api/mobile/towers/7/recipe", json={"recipe_idx": 2}, headers=headers)
            self.assertEqual(res_recipe.status_code, 202)
            self.assertEqual(res_recipe.json["desired"], "2")


class MobileServiceTest(unittest.TestCase):
    def reading(self, level=70, age=0):
        return {"nivel_agua": level, "utc_reading_time": datetime.now(timezone.utc) - timedelta(seconds=age)}

    def pump_mocks(self, row):
        stack = []
        for name, result in (
            ("owned_tower", TOWER),
            ("pump_row", {"modo": "manual"}),
            ("readings", [row]),
            ("configuration", {"nivel_minimo": 20}),
            ("_execute_transaction", [1, 1]),
        ):
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
        self.assertTrue(any("actuadores_torre" in call.args[0] for call in execute.call_args_list))

    def test_no_invented_tds_volume_or_nonfinite_sensors(self):
        result = service.sensors({"ec": 1.8, "ph": float("nan"), "nivel_agua": 70})
        self.assertEqual(result["ec_ms_cm"], 1.8)
        self.assertIsNone(result["ph"])
        self.assertIsNone(result["tds_ppm"])
        self.assertIsNone(result["litros"])

    def test_sensors_ingests_real_tds_and_liters(self):
        result = service.sensors({"ec": 1.5, "ph": 6.8, "tds_ppm": 750.0, "nivel_agua": 80.0, "volumen_litros": 24.0})
        self.assertEqual(result["tds_ppm"], 750.0)
        self.assertEqual(result["litros"], 24.0)
        self.assertEqual(result["nivel_pct"], 80.0)

    def test_persistent_command_sharing_across_workers(self):
        db_store = {}

        def mock_exec(query, params=None, fetchone=False, fetchall=False):
            if "INSERT INTO dispositivo_comandos" in query:
                cmd_id, t_id, action, desired, p_json, status, created, expires = params
                db_store[cmd_id] = {
                    "id_comando": cmd_id, "torre_id": t_id, "accion": action,
                    "estado_deseado": desired, "parametros_json": p_json,
                    "estado": status, "creado_en": created, "expira_en": expires
                }
            elif "SELECT * FROM dispositivo_comandos" in query:
                t_id = params[0]
                matching = [c for c in db_store.values() if c["torre_id"] == t_id]
                if "estado='pending'" in query:
                    matching = [c for c in matching if c["estado"] == "pending"]
                matching.sort(key=lambda x: (x["creado_en"], x["id_comando"]), reverse=True)
                return matching[0] if matching else None
            elif "SELECT id_comando, torre_id" in query:
                cmd_id, t_id = params
                row = db_store.get(cmd_id)
                if row and row["torre_id"] == t_id:
                    return row
                return None
            elif "UPDATE dispositivo_comandos SET estado=" in query and "WHERE id_comando=" in query:
                status, executed, ack, cmd_id, t_id = params
                row = db_store.get(cmd_id)
                if row and row["torre_id"] == t_id and row["estado"] == "pending":
                    row["estado"] = status
                    row["ejecutado_en"] = executed
            elif "UPDATE dispositivo_comandos SET estado='superseded'" in query:
                t_id = params[0]
                for c in db_store.values():
                    if c["torre_id"] == t_id and c["estado"] == "pending":
                        c["estado"] = "superseded"
            return None

        def mock_exec_tx(operations):
            for q, p in operations:
                mock_exec(q, p)
            return [1] * len(operations)

        with patch.object(service, "_execute", side_effect=mock_exec), patch.object(service, "_execute_transaction", side_effect=mock_exec_tx):
            # Worker 1: creates pump command
            cmd = service.create_pump_command(7, "on", ttl_sec=60)
            # Worker 2: queries DB directly
            active = service.get_active_command(7)
            self.assertIsNotNone(active)
            self.assertEqual(active["id"], cmd["id"])
            self.assertEqual(active["action"], "PUMP_ON")

            # Worker 3: records ACK
            ack_res = service.record_command_ack(7, cmd["id"], "EXECUTED_OK")
            self.assertIsNotNone(ack_res)
            self.assertEqual(ack_res["status"], "executed")
            # Verify in DB
            reloaded = service.get_active_command(7)
            self.assertEqual(reloaded["status"], "executed")

    def test_command_ack_ownership_isolated_between_towers(self):
        db_store = {}

        def mock_exec(query, params=None, fetchone=False, fetchall=False):
            if "INSERT INTO dispositivo_comandos" in query:
                cmd_id, t_id, action, desired, p_json, status, created, expires = params
                db_store[cmd_id] = {
                    "id_comando": cmd_id, "torre_id": t_id, "accion": action,
                    "estado_deseado": desired, "parametros_json": p_json,
                    "estado": status, "creado_en": created, "expira_en": expires
                }
            elif "SELECT id_comando, torre_id" in query:
                cmd_id, t_id = params
                row = db_store.get(cmd_id)
                if row and row["torre_id"] == t_id:
                    return row
                return None
            elif "UPDATE dispositivo_comandos SET estado=" in query and "WHERE id_comando=" in query:
                status, executed, ack, cmd_id, t_id = params
                row = db_store.get(cmd_id)
                if row and row["torre_id"] == t_id and row["estado"] == "pending":
                    row["estado"] = status
            elif "UPDATE dispositivo_comandos SET estado='superseded'" in query:
                t_id = params[0]
                for c in db_store.values():
                    if c["torre_id"] == t_id and c["estado"] == "pending":
                        c["estado"] = "superseded"
            return None

        def mock_exec_tx(operations):
            for q, p in operations:
                mock_exec(q, p)
            return [1] * len(operations)

        with patch.object(service, "_execute", side_effect=mock_exec), patch.object(service, "_execute_transaction", side_effect=mock_exec_tx):
            cmd1 = service.create_pump_command(7, "on", ttl_sec=60)
            cmd2 = service.create_pump_command(8, "off", ttl_sec=60)

            # Tower 8 tries to ACK Tower 7's command: must be rejected (returns None)
            res_bad = service.record_command_ack(8, cmd1["id"], "EXECUTED")
            self.assertIsNone(res_bad)
            self.assertEqual(db_store[cmd1["id"]]["estado"], "pending")

            # Tower 7 tries to ACK with invalid status: must be rejected
            res_invalid_status = service.record_command_ack(7, cmd1["id"], "UNSUPPORTED_STATUS")
            self.assertIsNone(res_invalid_status)
            self.assertEqual(db_store[cmd1["id"]]["estado"], "pending")

            # Wildcard ACK without command ID: must be rejected
            res_wildcard = service.record_command_ack(7, "", "EXECUTED")
            self.assertIsNone(res_wildcard)

            # Tower 7 ACKs its own command: accepted
            res_good = service.record_command_ack(7, cmd1["id"], "EXECUTED")
            self.assertIsNotNone(res_good)
            self.assertEqual(res_good["status"], "executed")
            self.assertEqual(db_store[cmd1["id"]]["estado"], "executed")

            # Re-ACKing an already executed command: rejected
            res_reack = service.record_command_ack(7, cmd1["id"], "EXECUTED")
            self.assertIsNone(res_reack)

            # Tower 8's command was never modified
            self.assertEqual(db_store[cmd2["id"]]["estado"], "pending")

    def test_command_persistence_failure_raises_503_without_memory_fallback(self):
        with patch.object(service, "_execute_transaction", side_effect=Error("DB connection lost")), patch.object(service, "_execute", return_value=None):
            with self.assertRaises(service.MobileError) as ctx:
                service.create_pump_command(7, "on")
            self.assertEqual(ctx.exception.status, 503)
            self.assertEqual(ctx.exception.code, "command_storage_failed")

            # With DB failing and no memory fallback, get_active_command returns None
            self.assertIsNone(service.get_active_command(7))

    def test_tower_detail_separates_pump_reported_from_mode_and_recipe(self):
        mock_pump_row = {"estado": "apagada", "modo": "manual", "ultimo_comando": "sin accion"}
        mock_cycle = {"id_ciclo": 1, "fase": "vegetativa", "notas": "", "cultivo_nombre": "Lechuga"}

        # Simulate that the latest command overall in DB is SET_MODE executed
        with patch.object(service, "owned_tower", return_value=TOWER), \
             patch.object(service, "readings", return_value=[]), \
             patch.object(service, "pump_row", return_value=mock_pump_row), \
             patch.object(service, "irrigation_row", return_value=None), \
             patch.object(service, "configuration", return_value={"deposito_litros": 5.0, "deposito_calibrado": False}), \
             patch.object(service, "get_active_pump_command", return_value=None), \
             patch.object(service, "_execute", side_effect=lambda q, *a, **k: mock_cycle if "ciclos_cultivo" in q else []):

            detail = service.tower_detail(7, 1)
            # pump.reported MUST be None (never 'AUTO' or '2')
            self.assertIsNone(detail["pump"]["reported"])
            self.assertEqual(detail["pump"]["desired"], "off")

    def test_liters_capability_and_volume_require_explicit_calibration(self):
        # 1. Without calibration: capabilities.liters is False
        mock_pump = {"estado": "apagada", "modo": "manual", "ultimo_comando": "sin accion"}
        with patch.object(service, "owned_tower", return_value=TOWER), \
             patch.object(service, "readings", return_value=[]), \
             patch.object(service, "pump_row", return_value=mock_pump), \
             patch.object(service, "irrigation_row", return_value=None), \
             patch.object(service, "get_active_pump_command", return_value=None), \
             patch.object(service, "_execute", return_value=[]):

            with patch.object(service, "configuration", return_value={"deposito_litros": 5.0, "deposito_calibrado": False}):
                detail_uncal = service.tower_detail(7, 1)
                self.assertFalse(detail_uncal["capabilities"]["liters"])

            with patch.object(service, "configuration", return_value={"deposito_litros": 5.0, "deposito_calibrado": True}):
                detail_cal = service.tower_detail(7, 1)
                self.assertTrue(detail_cal["capabilities"]["liters"])

    def test_sync_iot_device_volume_requires_explicit_calibration(self):
        from Conexión import conexion
        # 1. When deposito_calibrado is False in configuracion_control, volume remains None
        def mock_exec_uncal(q, *a, **k):
            if "configuracion_control" in q:
                return {"deposito_litros": 5.0, "deposito_calibrado": False}
            elif "actuadores_torre" in q:
                return {"modo": "automatico", "estado": "apagada", "ultimo_comando": "reporte_esp32"}
            return None

        with patch.object(conexion, "fetch_torre_by_codigo", return_value={"id_torre": 7}), \
             patch.object(conexion, "create_mysql_tables"), \
             patch.object(conexion, "_create_control_defaults_for_torre"), \
             patch.object(conexion, "insert_sensor_reading", return_value=123) as mock_insert, \
             patch.object(conexion, "_execute", side_effect=mock_exec_uncal):

            conexion.sync_iot_device(
                "TORRE-7", "esp32", nivel_agua=80.0, volumen_litros=None
            )
            self.assertIsNone(mock_insert.call_args.kwargs["volumen_litros"])

        # 2. When deposito_calibrado is True, volume is calculated from percentage and capacity
        def mock_exec_cal(q, *a, **k):
            if "configuracion_control" in q:
                return {"deposito_litros": 5.0, "deposito_calibrado": True}
            elif "actuadores_torre" in q:
                return {"modo": "automatico", "estado": "apagada", "ultimo_comando": "reporte_esp32"}
            return None

        with patch.object(conexion, "fetch_torre_by_codigo", return_value={"id_torre": 7}), \
             patch.object(conexion, "create_mysql_tables"), \
             patch.object(conexion, "_create_control_defaults_for_torre"), \
             patch.object(conexion, "insert_sensor_reading", return_value=124) as mock_insert, \
             patch.object(conexion, "_execute", side_effect=mock_exec_cal):

            conexion.sync_iot_device(
                "TORRE-7", "esp32", nivel_agua=80.0, volumen_litros=None
            )
            self.assertEqual(mock_insert.call_args.kwargs["volumen_litros"], 4.0)

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

    def test_sync_iot_device_persists_pump_state_in_manual_mode(self):
        from Conexión import conexion
        executed_updates = []
        def mock_exec(q, params=None, **k):
            if "SELECT modo FROM actuadores_torre" in q:
                return {"modo": "manual"}
            if "UPDATE actuadores_torre" in q:
                executed_updates.append(params)
                return None
            return None

        with patch.object(conexion, "fetch_torre_by_codigo", return_value={"id_torre": 7}), \
             patch.object(conexion, "create_mysql_tables"), \
             patch.object(conexion, "_create_control_defaults_for_torre"), \
             patch.object(conexion, "_execute", side_effect=mock_exec):

            # Dispositivo reporta que la bomba se apagó físicamente (rele_principal_on=False)
            conexion.sync_iot_device("TORRE-7", "esp32_ecogrow2", rele_principal_on=False)

            self.assertEqual(len(executed_updates), 1)
            estado, modo, ultimo_comando, torre_id, tipo = executed_updates[0]
            self.assertEqual(estado, "apagada")
            self.assertEqual(modo, "manual")
            self.assertEqual(ultimo_comando, "reporte_esp32_ecogrow2")
            self.assertEqual(torre_id, 7)
            self.assertEqual(tipo, "bomba_principal")

    def test_pump_reported_reflects_physical_reading_never_executed_command_ack(self):
        # Escenario auditado: ON solicitado -> ejecutado por comando -> apagado físico por botón o timeout -> sync_iot OFF
        # El comando activo está 'executed' con desired='on', pero la lectura física del actuador es 'apagada'.
        executed_cmd = {
            "id": "cmd_12345",
            "action": "PUMP_ON",
            "desired": "on",
            "created_at": int(time.time()) - 300,
            "expires_at": int(time.time()) + 300,
            "ttl_sec": 60,
            "status": "executed",
        }
        # Caso 1: Lectura física presente indicando apagada -> reported DEBE ser 'off'
        pump_phys_off = {"estado": "apagada", "modo": "manual", "ultimo_comando": "reporte_esp32_ecogrow2"}
        with patch.object(service, "owned_tower", return_value=TOWER), \
             patch.object(service, "readings", return_value=[]), \
             patch.object(service, "pump_row", return_value=pump_phys_off), \
             patch.object(service, "irrigation_row", return_value=None), \
             patch.object(service, "configuration", return_value={}), \
             patch.object(service, "get_active_pump_command", return_value=executed_cmd), \
             patch.object(service, "_execute", return_value=[]):

            detail = service.tower_detail(7, 1)
            # Ambas interfaces ven el reporte físico real: 'off' (apagada/detenida), NUNCA 'on' del comando ejecutado
            self.assertEqual(detail["pump"]["reported"], "off")
            self.assertEqual(detail["pump"]["desired"], "on")
            self.assertEqual(detail["pump"]["status"], "executed")

        # Caso 2: Sin lectura física reportada por actuador -> reported DEBE ser None (no inventar 'on')
        pump_no_report = {"estado": "encendida", "modo": "manual", "ultimo_comando": "panel_web"}
        with patch.object(service, "owned_tower", return_value=TOWER), \
             patch.object(service, "readings", return_value=[]), \
             patch.object(service, "pump_row", return_value=pump_no_report), \
             patch.object(service, "irrigation_row", return_value=None), \
             patch.object(service, "configuration", return_value={}), \
             patch.object(service, "get_active_pump_command", return_value=executed_cmd), \
             patch.object(service, "_execute", return_value=[]):

            detail2 = service.tower_detail(7, 1)
            self.assertIsNone(detail2["pump"]["reported"])


if __name__ == "__main__":
    unittest.main()
