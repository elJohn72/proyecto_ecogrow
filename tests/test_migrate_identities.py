"""Pruebas unitarias para la herramienta de migración de identidades antiguas EcoGrow 2.0."""

import unittest
from unittest.mock import MagicMock, patch

from tools.migrate_identities import (
    apply_migrations,
    audit_identities,
    derive_canonical_code,
    is_placeholder_code,
)


class TestMigrateIdentities(unittest.TestCase):
    def test_is_placeholder_code(self):
        self.assertTrue(is_placeholder_code("TORRE-001"))
        self.assertTrue(is_placeholder_code("EG-TORRE-01"))
        self.assertTrue(is_placeholder_code("DUMMY"))
        self.assertTrue(is_placeholder_code("PRUEBA"))
        self.assertTrue(is_placeholder_code("TEST"))
        self.assertTrue(is_placeholder_code("IDENTIFICADOR_TECNICO"))
        self.assertTrue(is_placeholder_code(""))
        self.assertTrue(is_placeholder_code(None))

        # Canónicos válidos
        self.assertFalse(is_placeholder_code("EG-TORRE-F870C4"))
        self.assertFalse(is_placeholder_code("TORRE-HUERTO-A"))
        self.assertFalse(is_placeholder_code("EG-TORRE-123456"))

    def test_derive_canonical_code(self):
        self.assertEqual(derive_canonical_code("44:1D:64:F8:70:C4"), "EG-TORRE-F870C4")
        self.assertEqual(derive_canonical_code("44-1d-64-f8-70-c4"), "EG-TORRE-F870C4")
        self.assertEqual(derive_canonical_code("441d64f870c4"), "EG-TORRE-F870C4")

        with self.assertRaises(ValueError):
            derive_canonical_code("INVALID_MAC")

    @patch("Conexión.conexion._connect")
    @patch("Conexión.conexion.create_mysql_tables")
    def test_audit_identities(self, mock_create, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            {"id_dispositivo": 1, "codigo_torre": "TORRE-001", "mac": "44:1D:64:F8:70:C4", "estado": "fabrica", "reclamado_por": None},
            {"id_dispositivo": 2, "codigo_torre": "EG-TORRE-AABBCC", "mac": "11:22:33:AA:BB:CC", "estado": "reclamada", "reclamado_por": 5},
        ]

        items = audit_identities(conn_func=lambda: mock_conn)
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["is_placeholder"])
        self.assertEqual(items[0]["action"], "MIGRATE_TO_CANONICAL")
        self.assertEqual(items[0]["canonical_code"], "EG-TORRE-F870C4")

        self.assertFalse(items[1]["is_placeholder"])
        self.assertEqual(items[1]["action"], "OK")
        self.assertEqual(items[1]["canonical_code"], "EG-TORRE-AABBCC")

    @patch("Conexión.conexion._connect")
    @patch("Conexión.conexion.create_mysql_tables")
    def test_apply_migrations_dry_run(self, mock_create, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            {"id_dispositivo": 1, "codigo_torre": "TORRE-001", "mac": "44:1D:64:F8:70:C4", "estado": "fabrica", "reclamado_por": None},
        ]
        mock_cursor.fetchone.return_value = None  # No conflict

        res = apply_migrations(dry_run=True, conn_func=lambda: mock_conn)
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["total_checked"], 1)
        self.assertEqual(res["migrated"], 1)
        self.assertEqual(res["details"][0]["status"], "PROPOSED")
        self.assertEqual(res["details"][0]["new_code"], "EG-TORRE-F870C4")
        mock_conn.commit.assert_not_called()
        sqls = [call.args[0] for call in mock_cursor.execute.call_args_list]
        self.assertFalse(any(sql.strip().upper().startswith("UPDATE") for sql in sqls))

    @patch("Conexión.conexion._connect")
    @patch("Conexión.conexion.create_mysql_tables")
    def test_apply_migrations_real(self, mock_create, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            {"id_dispositivo": 1, "codigo_torre": "TORRE-001", "mac": "44:1D:64:F8:70:C4", "estado": "reclamada", "reclamado_por": 42},
        ]
        mock_cursor.fetchone.return_value = None  # No conflict

        res = apply_migrations(dry_run=False, conn_func=lambda: mock_conn)
        self.assertFalse(res["dry_run"])
        self.assertEqual(res["total_checked"], 1)
        self.assertEqual(res["migrated"], 1)
        self.assertEqual(res["details"][0]["status"], "MIGRATED")
        mock_conn.commit.assert_called_once()
        sqls = [call.args[0] for call in mock_cursor.execute.call_args_list]
        torre_updates = [sql for sql in sqls if "UPDATE torres" in sql]
        self.assertTrue(torre_updates)
        self.assertTrue(all("codigo_unico" in sql for sql in torre_updates))
        self.assertFalse(any("codigo_torre" in sql for sql in torre_updates))
        self.assertTrue(any("UPDATE dispositivos_iot" in sql and "codigo_torre" in sql for sql in sqls))

    @patch("Conexión.conexion._connect")
    @patch("Conexión.conexion.create_mysql_tables")
    def test_apply_stops_on_tower_code_conflict(self, mock_create, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {"id_dispositivo": 1, "codigo_torre": "TORRE-001", "mac": "44:1D:64:F8:70:C4", "estado": "reclamada", "reclamado_por": 42},
        ]
        mock_cursor.fetchone.side_effect = [
            None,
            {"id_torre": 9, "usuario_id": 3},
        ]

        result = apply_migrations(dry_run=False, conn_func=lambda: mock_conn)
        self.assertEqual(result["migrated"], 0)
        self.assertEqual(result["requires_workshop"], 1)
        self.assertEqual(result["details"][0]["status"], "CONFLICT")
        self.assertEqual(result["details"][0]["conflict_table"], "torres")
        sqls = [call.args[0] for call in mock_cursor.execute.call_args_list]
        self.assertFalse(any(sql.strip().upper().startswith("UPDATE") for sql in sqls))
        mock_conn.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
