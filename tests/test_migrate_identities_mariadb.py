"""Integración MariaDB de la migración de identidades.

No usa la base del VPS. Crea una base temporal y la elimina al terminar.
Si MariaDB no está disponible, la clase se omite.
"""

import os
import unittest
import uuid

from Conexión import conexion
from tools.migrate_identities import apply_migrations


class MigrateIdentitiesMariaDBTest(unittest.TestCase):
    temp_db = None
    orig_config = None
    orig_env_db = None

    @classmethod
    def setUpClass(cls):
        try:
            conn = conexion._connect(include_database=False)
            conn.close()
        except Exception:
            raise unittest.SkipTest("MariaDB/MySQL no está disponible para la migración real.")

        cls.orig_config = dict(conexion.MYSQL_CONFIG)
        cls.orig_env_db = os.environ.get("MYSQL_DATABASE")
        cls.temp_db = f"ecogrow_mig_{uuid.uuid4().hex[:8]}"
        os.environ["MYSQL_DATABASE"] = cls.temp_db
        conexion.MYSQL_CONFIG["database"] = cls.temp_db
        conexion.create_mysql_tables()

    @classmethod
    def tearDownClass(cls):
        if cls.temp_db:
            try:
                conn = conexion._connect(include_database=False)
                with conn.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS `{cls.temp_db}`")
                conn.commit()
                conn.close()
            except Exception:
                pass
        if cls.orig_config:
            conexion.MYSQL_CONFIG.update(cls.orig_config)
        if cls.orig_env_db is not None:
            os.environ["MYSQL_DATABASE"] = cls.orig_env_db
        else:
            os.environ.pop("MYSQL_DATABASE", None)

    def setUp(self):
        for table in (
            "eventos_cosecha",
            "eventos_control",
            "lecturas_sensores",
            "dispositivo_comandos",
            "alertas_sistema",
            "programaciones_riego",
            "actuadores_torre",
            "configuracion_control",
            "ciclos_cultivo",
            "fases_cultivo",
            "cultivos",
            "dispositivos_iot",
            "torres",
            "usuarios",
        ):
            conexion._execute(f"DELETE FROM {table}")

    def _seed_linked_tower(self, user_id, mail, code, mac, token, tower_name):
        conexion._execute(
            "INSERT INTO usuarios (id_usuario, nombre, mail, password) VALUES (%s, %s, %s, %s)",
            (user_id, "PRUEBA", mail, "PRUEBA-hash"),
        )
        tower_id = conexion._execute(
            """
            INSERT INTO torres (usuario_id, nombre, ubicacion, codigo_unico, estado)
            VALUES (%s, %s, %s, %s, 'activo')
            """,
            (user_id, tower_name, "PRUEBA", code),
        )
        conexion._execute(
            "INSERT INTO configuracion_control (torre_id, deposito_calibrado) VALUES (%s, TRUE)",
            (tower_id,),
        )
        cultivo_id = conexion._execute(
            """
            INSERT INTO cultivos (usuario_id, nombre, variedad, ubicacion, estado, descripcion)
            VALUES (%s, 'PRUEBA', 'PRUEBA', 'PRUEBA', 'activo', 'PRUEBA')
            """,
            (user_id,),
        )
        ciclo_id = conexion._execute(
            "INSERT INTO ciclos_cultivo (torre_id, cultivo_id, fase) VALUES (%s, %s, 'PRUEBA')",
            (tower_id, cultivo_id),
        )
        lectura_id = conexion._execute(
            "INSERT INTO lecturas_sensores (ciclo_id, dispositivo, ph) VALUES (%s, 'PRUEBA', 6.20)",
            (ciclo_id,),
        )
        device_id = conexion._execute(
            """
            INSERT INTO dispositivos_iot
                (codigo_torre, mac, pop_hash, device_token, estado, reclamado_por)
            VALUES (%s, %s, %s, %s, 'reclamada', %s)
            """,
            (code, mac, "a" * 64, token, user_id),
        )
        return tower_id, lectura_id, device_id

    def test_real_sql_preserves_owner_history_and_is_idempotent(self):
        tower_id, lectura_id, device_id = self._seed_linked_tower(
            7, "prueba-mig@example.com", "TORRE-001", "44:1D:64:F8:70:C4", "token-prueba-mig-001", "Torre PRUEBA"
        )
        first = apply_migrations(dry_run=False)
        self.assertEqual(first["migrated"], 1)
        self.assertEqual(first["details"][0]["new_code"], "EG-TORRE-F870C4")
        self.assertEqual(first["details"][0]["id_torre"], tower_id)
        self.assertEqual(first["details"][0]["usuario_id"], 7)

        tower = conexion._execute("SELECT id_torre, usuario_id, codigo_unico, nombre FROM torres WHERE id_torre = %s", (tower_id,), fetchone=True)
        device = conexion._execute("SELECT id_dispositivo, codigo_torre, reclamado_por, estado, device_token FROM dispositivos_iot WHERE id_dispositivo = %s", (device_id,), fetchone=True)
        config = conexion._execute("SELECT torre_id, deposito_calibrado FROM configuracion_control WHERE torre_id = %s", (tower_id,), fetchone=True)
        lectura = conexion._execute("SELECT id_lectura, ph FROM lecturas_sensores WHERE id_lectura = %s", (lectura_id,), fetchone=True)

        self.assertEqual(tower["id_torre"], tower_id)
        self.assertEqual(tower["usuario_id"], 7)
        self.assertEqual(tower["codigo_unico"], "EG-TORRE-F870C4")
        self.assertEqual(tower["nombre"], "Torre PRUEBA")
        self.assertEqual(device["codigo_torre"], "EG-TORRE-F870C4")
        self.assertEqual(device["reclamado_por"], 7)
        self.assertEqual(device["estado"], "reclamada")
        self.assertEqual(device["device_token"], "token-prueba-mig-001")
        self.assertEqual(config["torre_id"], tower_id)
        self.assertEqual(int(lectura["id_lectura"]), lectura_id)
        self.assertEqual(float(lectura["ph"]), 6.2)

        second = apply_migrations(dry_run=False)
        self.assertEqual(second["migrated"], 0)
        self.assertEqual(second["skipped_canonical"], 1)
        again = conexion._execute("SELECT codigo_unico, usuario_id FROM torres WHERE id_torre = %s", (tower_id,), fetchone=True)
        self.assertEqual(again["codigo_unico"], "EG-TORRE-F870C4")
        self.assertEqual(again["usuario_id"], 7)

    def test_real_sql_conflict_on_device_and_tower_does_not_write(self):
        self._seed_linked_tower(
            8, "prueba-conflicto@example.com", "TORRE-001", "44:1D:64:F8:70:C4", "token-prueba-mig-002", "Origen"
        )
        conexion._execute(
            "INSERT INTO usuarios (id_usuario, nombre, mail, password) VALUES (%s, %s, %s, %s)",
            (9, "PRUEBA", "prueba-otro@example.com", "PRUEBA-hash"),
        )
        conexion._execute(
            """
            INSERT INTO dispositivos_iot (codigo_torre, mac, pop_hash, device_token, estado)
            VALUES ('EG-TORRE-F870C4', '11:22:33:44:55:66', %s, 'token-prueba-mig-003', 'fabrica')
            """,
            ("b" * 64,),
        )
        device_result = apply_migrations(dry_run=False)
        self.assertEqual(device_result["migrated"], 0)
        self.assertEqual(device_result["details"][0]["conflict_table"], "dispositivos_iot")
        still = conexion._execute("SELECT codigo_torre, reclamado_por FROM dispositivos_iot WHERE mac = %s", ("44:1D:64:F8:70:C4",), fetchone=True)
        self.assertEqual(still["codigo_torre"], "TORRE-001")
        self.assertEqual(still["reclamado_por"], 8)

        conexion._execute("DELETE FROM dispositivos_iot WHERE mac = %s", ("11:22:33:44:55:66",))
        conexion._execute(
            """
            INSERT INTO torres (usuario_id, nombre, ubicacion, codigo_unico, estado)
            VALUES (9, 'Otra', 'PRUEBA', 'EG-TORRE-F870C4', 'activo')
            """
        )
        tower_result = apply_migrations(dry_run=False)
        self.assertEqual(tower_result["migrated"], 0)
        self.assertEqual(tower_result["details"][0]["conflict_table"], "torres")
        origin = conexion._execute("SELECT codigo_unico, usuario_id FROM torres WHERE nombre = 'Origen'", fetchone=True)
        other = conexion._execute("SELECT usuario_id FROM torres WHERE codigo_unico = 'EG-TORRE-F870C4'", fetchone=True)
        self.assertEqual(origin["codigo_unico"], "TORRE-001")
        self.assertEqual(origin["usuario_id"], 8)
        self.assertEqual(other["usuario_id"], 9)

    def test_transaction_rollback_keeps_previous_code(self):
        tower_id, _, _ = self._seed_linked_tower(
            10, "prueba-rollback@example.com", "DUMMY", "AA:BB:CC:DD:EE:01", "token-prueba-mig-004", "Rollback"
        )

        def fail_before_commit(_cursor):
            raise RuntimeError("fallo antes de commit")

        with self.assertRaises(RuntimeError):
            apply_migrations(dry_run=False, before_commit=fail_before_commit)

        tower = conexion._execute("SELECT codigo_unico, usuario_id FROM torres WHERE id_torre = %s", (tower_id,), fetchone=True)
        device = conexion._execute("SELECT codigo_torre, reclamado_por FROM dispositivos_iot WHERE mac = %s", ("AA:BB:CC:DD:EE:01",), fetchone=True)
        self.assertEqual(tower["codigo_unico"], "DUMMY")
        self.assertEqual(tower["usuario_id"], 10)
        self.assertEqual(device["codigo_torre"], "DUMMY")
        self.assertEqual(device["reclamado_por"], 10)


if __name__ == "__main__":
    unittest.main()
