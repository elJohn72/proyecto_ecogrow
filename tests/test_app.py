import unittest
from unittest.mock import patch

from app import app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["ADMIN_EMAILS"] = set()
        self.client = app.test_client()

    def _login_session(self, mail="demo@correo.com", ui_mode=None):
        with self.client.session_transaction() as session:
            session["_user_id"] = "1"
            session["_fresh"] = True
            if ui_mode is not None:
                session["ui_mode"] = ui_mode

        return {
            "id_usuario": 1,
            "nombre": "Demo",
            "mail": mail,
            "password": "hash",
        }

    def test_public_pages_load(self):
        for route in ("/", "/login", "/registro", "/demo", "/privacidad", "/about", "/contactos"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json().get("status"), "ok")

    def test_seo_routes_exist(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn(b"Sitemap:", robots.data)

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn(b"<urlset", sitemap.data)

    def test_protected_route_redirects_to_login(self):
        for route in ("/dashboard", "/agricultor-ia"):
            response = self.client.get(route, follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login", response.headers["Location"])

    def test_login_page_renders_csrf_token(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"csrf_token", response.data)

    def test_form_post_without_csrf_is_rejected(self):
        response = self.client.post(
            "/login",
            data={"mail": "demo@correo.com", "password": "12345678"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    def test_login_with_valid_credentials_redirects_to_torres(self):
        with self.client.session_transaction() as session:
            session["csrf_token"] = "token-prueba"

        with patch("blueprints.auth.verify_mysql_user_credentials") as verify_credentials, patch(
            "blueprints.auth.fetch_torres_by_user"
        ) as fetch_torres:
            verify_credentials.return_value = {
                "id_usuario": 1,
                "nombre": "Demo",
                "mail": "demo@correo.com",
                "password": "hash",
            }
            fetch_torres.return_value = []

            response = self.client.post(
                "/login",
                data={
                    "csrf_token": "token-prueba",
                    "mail": "demo@correo.com",
                    "password": "12345678",
                },
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/torres", response.headers["Location"])

    def test_iot_sync_requires_token(self):
        response = self.client.post("/api/iot/sync", json={"torre_codigo": "TORRE01", "dispositivo": "esp"})
        self.assertEqual(response.status_code, 401)

    def test_iot_sync_returns_rele_command(self):
        with patch("blueprints.sensores.sync_iot_device") as sync_device:
            sync_device.return_value = {
                "torre_id": 1,
                "lectura_id": None,
                "sensor_warning": None,
                "comandos": {"rele_principal": "apagado"},
                "actuador": {"estado": "apagada", "modo": "manual", "ultimo_comando": "panel"},
            }
            response = self.client.post(
                "/api/iot/sync",
                headers={"X-API-Token": app.config["SENSOR_API_TOKEN"]},
                json={
                    "torre_codigo": "TORRE01",
                    "dispositivo": "esp32_rele_01",
                    "rele_principal": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["comandos"]["rele_principal"], "apagado")

    def test_sensor_api_requires_token(self):
        response = self.client.post("/api/sensores/lectura", json={})
        self.assertEqual(response.status_code, 401)

    def test_sensor_api_validates_required_fields_after_token(self):
        response = self.client.post(
            "/api/sensores/lectura",
            headers={"X-API-Token": app.config["SENSOR_API_TOKEN"]},
            json={"dispositivo": "esp32-demo"},
        )
        self.assertEqual(response.status_code, 400)

    def test_regular_user_cannot_enable_admin_mode(self):
        user_row = self._login_session(ui_mode="user")

        with patch("app.fetch_mysql_usuario", return_value=user_row):
            response = self.client.get("/modo/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])
        with self.client.session_transaction() as session:
            self.assertEqual(session.get("ui_mode"), "user")

    def test_regular_user_cannot_access_admin_route_by_session_flag(self):
        user_row = self._login_session(ui_mode="admin")

        with patch("app.fetch_mysql_usuario", return_value=user_row):
            response = self.client.get("/mysql", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    def test_logged_user_can_open_torre_registration(self):
        user_row = self._login_session(ui_mode="user")

        with patch("app.fetch_mysql_usuario", return_value=user_row):
            response = self.client.get("/torres/registrar", follow_redirects=False)

        self.assertEqual(response.status_code, 200)

    def test_logged_user_can_open_cultivo_creation(self):
        user_row = self._login_session(ui_mode="user")

        with self.client.session_transaction() as session:
            session["torre_id"] = 1

        with patch("app.fetch_mysql_usuario", return_value=user_row), patch(
            "blueprints.shared.fetch_torre",
            return_value={
                "id_torre": 1,
                "codigo_unico": "TORRE01",
                "nombre": "Torre Demo",
                "ubicacion": "Laboratorio",
                "estado": "activa",
            },
        ):
            response = self.client.get("/cultivos/nuevo", follow_redirects=False)

        self.assertEqual(response.status_code, 200)

    def test_admin_user_can_enable_admin_mode(self):
        app.config["ADMIN_EMAILS"] = {"admin@correo.com"}
        user_row = self._login_session(mail="admin@correo.com", ui_mode="user")

        with patch("app.fetch_mysql_usuario", return_value=user_row):
            response = self.client.get("/modo/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session.get("ui_mode"), "admin")

    def test_regular_user_does_not_see_admin_cultivos_columns(self):
        user_row = self._login_session(ui_mode="admin")

        with self.client.session_transaction() as session:
            session["torre_id"] = 1

        with patch("app.fetch_mysql_usuario", return_value=user_row), patch(
            "blueprints.cultivos.fetch_cultivos", return_value=[]
        ), patch("blueprints.cultivos.fetch_active_cycle_by_torre", return_value=None), patch(
            "blueprints.cultivos.fetch_cycles_by_torre", return_value=[{"id_ciclo": 1}]
        ), patch("blueprints.cultivos.fetch_latest_sensor_reading_by_torre", return_value=None), patch(
            "blueprints.shared.fetch_torre",
            return_value={
                "id_torre": 1,
                "codigo_unico": "TORRE01",
                "nombre": "Torre Demo",
                "ubicacion": "Lab",
                "estado": "activa",
            },
        ):
            response = self.client.get("/cultivos", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Ubicacion", response.data)
        self.assertNotIn(b"Visible solo en modo administrador", response.data)

    def test_logged_user_can_open_harvest_form_with_active_cycle(self):
        user_row = self._login_session(ui_mode="user")

        with self.client.session_transaction() as session:
            session["torre_id"] = 1

        torre = {
            "id_torre": 1,
            "usuario_id": 1,
            "codigo_unico": "TORRE01",
            "nombre": "Torre Demo",
            "ubicacion": "Lab",
            "estado": "activa",
        }
        ciclo = {
            "id_ciclo": 10,
            "cultivo_id": 2,
            "cultivo_nombre": "Lechuga",
            "fase": "cosecha",
            "notas": "",
        }

        with patch("app.fetch_mysql_usuario", return_value=user_row), patch(
            "blueprints.shared.fetch_torre", return_value=torre
        ), patch("blueprints.torres.fetch_active_cycle_by_torre", return_value=ciclo), patch(
            "blueprints.torres.fetch_harvests_by_torre", return_value=[]
        ):
            response = self.client.get("/torres/cultivo/cosecha", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registrar cosecha", response.data)

    def test_logged_user_can_open_torre_configuration(self):
        user_row = self._login_session(ui_mode="user")

        with self.client.session_transaction() as session:
            session["torre_id"] = 1

        torre = {
            "id_torre": 1,
            "usuario_id": 1,
            "codigo_unico": "TORRE01",
            "nombre": "Torre Demo",
            "ubicacion": "Lab",
            "estado": "activa",
        }
        config = {
            "module_size_mm": 80,
            "deposito_litros": 5.0,
            "bomba_modelo": "Bomba 12V",
            "head_height_m": 1.4,
            "ph_min": 5.5,
            "ph_max": 6.5,
            "ec_min": 1.4,
            "ec_max": 2.4,
            "temperatura_agua_min": 18.0,
            "temperatura_agua_max": 24.0,
            "nivel_minimo": 20.0,
            "nivel_objetivo": 85.0,
            "irrigation_on_minutes": 15,
            "irrigation_off_minutes": 60,
        }

        with patch("app.fetch_mysql_usuario", return_value=user_row), patch(
            "blueprints.shared.fetch_torre", return_value=torre
        ), patch("blueprints.torres.fetch_control_configuration", return_value=config), patch(
            "blueprints.torres.fetch_irrigation_schedule",
            return_value={
                "habilitado": True,
                "minutos_encendido": 15,
                "minutos_apagado": 60,
                "estrategia": "oxigenacion_radicular",
            },
        ), patch("blueprints.torres.fetch_effective_control_configuration", return_value=config), patch(
            "blueprints.torres.fetch_active_cycle_by_torre", return_value=None
        ):
            response = self.client.get("/torres/configuracion", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Configuracion de Torre Demo", response.data)


if __name__ == "__main__":
    unittest.main()
