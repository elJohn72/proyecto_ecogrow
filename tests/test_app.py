import unittest
from unittest.mock import patch

from app import app


class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_public_pages_load(self):
        for route in ("/", "/login", "/registro", "/demo"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)

    def test_protected_route_redirects_to_login(self):
        response = self.client.get("/dashboard", follow_redirects=False)
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


if __name__ == "__main__":
    unittest.main()
