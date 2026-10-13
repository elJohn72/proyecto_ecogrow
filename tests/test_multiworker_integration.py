"""Integration tests with real MariaDB and multiple OS processes.

Validates multi-worker persistence, concurrency, atomic rollbacks,
cross-tower isolation, and lifecycle of commands in EcoGrow 2.0.
"""
import multiprocessing
import os
import time
import unittest
import uuid

from Conexión import conexion
from services import mobile_service


def _worker_create_command(cfg, tower_id, desired_state, ttl_sec, queue):
    """Worker process: persists a new pump command."""
    try:
        conexion.MYSQL_CONFIG.update(cfg)
        os.environ["MYSQL_DATABASE"] = cfg["database"]
        cmd = mobile_service.create_pump_command(tower_id, desired_state, ttl_sec=ttl_sec)
        queue.put({"success": True, "cmd": cmd})
    except Exception as exc:
        queue.put({"success": False, "error": str(exc)})


def _worker_poll_command(cfg, tower_id, queue):
    """Worker process: queries the active pending command."""
    try:
        conexion.MYSQL_CONFIG.update(cfg)
        os.environ["MYSQL_DATABASE"] = cfg["database"]
        cmd = mobile_service.get_active_command(tower_id)
        queue.put({"success": True, "cmd": cmd})
    except Exception as exc:
        queue.put({"success": False, "error": str(exc)})


def _worker_ack_command(cfg, tower_id, cmd_id, ack_status, queue):
    """Worker process: records command execution/acknowledgement."""
    try:
        conexion.MYSQL_CONFIG.update(cfg)
        os.environ["MYSQL_DATABASE"] = cfg["database"]
        res = mobile_service.record_command_ack(tower_id, cmd_id, ack_status)
        queue.put({"success": True, "result": res})
    except Exception as exc:
        queue.put({"success": False, "error": str(exc)})


def _worker_concurrent_create(cfg, tower_id, cmd_type, value, queue):
    """Worker process: creates commands concurrently."""
    try:
        conexion.MYSQL_CONFIG.update(cfg)
        os.environ["MYSQL_DATABASE"] = cfg["database"]
        if cmd_type == "pump":
            cmd = mobile_service.create_pump_command(tower_id, value, ttl_sec=60)
        elif cmd_type == "mode":
            cmd = mobile_service.create_mode_command(tower_id, value, ttl_sec=60)
        elif cmd_type == "recipe":
            cmd = mobile_service.create_recipe_command(tower_id, int(value), ttl_sec=60)
        else:
            raise ValueError(f"Unknown cmd_type: {cmd_type}")
        queue.put({"success": True, "cmd": cmd})
    except Exception as exc:
        queue.put({"success": False, "error": str(exc)})


class MultiworkerIntegrationTest(unittest.TestCase):
    temp_db = None
    orig_config = None
    orig_env_db = None

    @classmethod
    def setUpClass(cls):
        # Verify real database connectivity
        try:
            conn = conexion._connect(include_database=False)
            conn.close()
        except Exception:
            raise unittest.SkipTest("MariaDB/MySQL no está disponible para pruebas de integración con base de datos real.")

        cls.orig_config = dict(conexion.MYSQL_CONFIG)
        cls.orig_env_db = os.environ.get("MYSQL_DATABASE")

        # Unique temporary database
        cls.temp_db = f"ecogrow_temp_test_{uuid.uuid4().hex[:8]}"
        os.environ["MYSQL_DATABASE"] = cls.temp_db
        conexion.MYSQL_CONFIG["database"] = cls.temp_db

        # Initialize schema
        conexion.create_mysql_tables()

        # Seed test user and towers
        cls._seed_database()

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

    @classmethod
    def _seed_database(cls):
        conexion._execute(
            """INSERT INTO usuarios (id_usuario, nombre, mail, password)
               VALUES (1, 'Usuario Integración', 'worker_test@example.com', 'test_hash')
               ON DUPLICATE KEY UPDATE nombre=VALUES(nombre)"""
        )
        conexion._execute(
            """INSERT INTO torres (id_torre, usuario_id, nombre, ubicacion, codigo_unico, estado)
               VALUES (1, 1, 'Torre A', 'Invernadero A', 'TORRE-TEST-01', 'activo'),
                      (2, 1, 'Torre B', 'Invernadero B', 'TORRE-TEST-02', 'activo')
               ON DUPLICATE KEY UPDATE nombre=VALUES(nombre)"""
        )

    def setUp(self):
        # Clean commands table between test cases
        conexion._execute("DELETE FROM dispositivo_comandos")

    def test_multiworker_lifecycle_create_poll_ack(self):
        """Worker 1 creates command, Worker 2 reads it, Worker 3 ACKs it.

        All executed by independent OS processes against real MariaDB.
        """
        cfg = dict(conexion.MYSQL_CONFIG)

        # 1. Worker 1 creates PUMP_ON command
        q1 = multiprocessing.Queue()
        p1 = multiprocessing.Process(target=_worker_create_command, args=(cfg, 1, "on", 60, q1))
        p1.start()
        p1.join(timeout=10)
        res1 = q1.get(timeout=2)
        self.assertTrue(res1["success"], res1.get("error"))
        cmd_id = res1["cmd"]["id"]
        self.assertTrue(cmd_id.startswith("cmd_"))

        # 2. Worker 2 polls the command from another process
        q2 = multiprocessing.Queue()
        p2 = multiprocessing.Process(target=_worker_poll_command, args=(cfg, 1, q2))
        p2.start()
        p2.join(timeout=10)
        res2 = q2.get(timeout=2)
        self.assertTrue(res2["success"], res2.get("error"))
        polled_cmd = res2["cmd"]
        self.assertIsNotNone(polled_cmd)
        self.assertEqual(polled_cmd["id"], cmd_id)
        self.assertEqual(polled_cmd["action"], "PUMP_ON")
        self.assertEqual(polled_cmd["desired"], "on")
        self.assertEqual(polled_cmd["status"], "pending")

        # 3. Worker 3 ACKs the command as executed
        q3 = multiprocessing.Queue()
        p3 = multiprocessing.Process(target=_worker_ack_command, args=(cfg, 1, cmd_id, "executed", q3))
        p3.start()
        p3.join(timeout=10)
        res3 = q3.get(timeout=2)
        self.assertTrue(res3["success"], res3.get("error"))
        ack_res = res3["result"]
        self.assertIsNotNone(ack_res)
        self.assertEqual(ack_res["id"], cmd_id)
        self.assertEqual(ack_res["status"], "executed")

        # 4. Verify persistent state in DB
        active = mobile_service.get_active_pump_command(1)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], cmd_id)
        self.assertEqual(active["status"], "executed")

    def test_atomic_rollback_on_transaction_failure(self):
        """If an operation fails during command creation, rollback is complete.

        The previous pending command is NOT marked superseded and remains valid.
        """
        # Step 1: Create an initial valid command
        cmd1 = mobile_service.create_pump_command(1, "on", ttl_sec=60)
        self.assertEqual(cmd1["status"], "pending")

        # Step 2: Attempt a transaction that supersedes previous and inserts an INVALID query
        with self.assertRaises(Exception):
            conexion._execute_transaction([
                ("UPDATE dispositivo_comandos SET estado='superseded' WHERE torre_id=%s AND estado='pending'", (1,)),
                ("INSERT INTO tabla_inexistente_que_falla_seguro (col) VALUES (%s)", ("valor",)),
            ])

        # Step 3: Verify rollback: cmd1 MUST still be 'pending', not 'superseded'
        row = conexion._execute(
            "SELECT id_comando, estado FROM dispositivo_comandos WHERE id_comando=%s",
            (cmd1["id"],),
            fetchone=True,
        )
        self.assertEqual(row["estado"], "pending")

        # Active command is still cmd1
        active = mobile_service.get_active_command(1)
        self.assertEqual(active["id"], cmd1["id"])
        self.assertEqual(active["status"], "pending")

    def test_deterministic_ordering_under_concurrency(self):
        """Multiple concurrent workers issuing orders for the same tower.

        MariaDB enforces atomic ordering: exactly ONE command ends up pending,
        and all earlier commands are marked superseded.
        """
        cfg = dict(conexion.MYSQL_CONFIG)
        commands_to_send = [
            ("pump", "on"),
            ("pump", "off"),
            ("mode", "MANUAL"),
            ("recipe", 2),
        ]

        queues = []
        processes = []
        for cmd_type, val in commands_to_send:
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=_worker_concurrent_create, args=(cfg, 1, cmd_type, val, q))
            queues.append(q)
            processes.append(p)

        # Launch all concurrently
        for p in processes:
            p.start()

        # Wait for all to finish
        for p in processes:
            p.join(timeout=10)

        results = [q.get(timeout=2) for q in queues]
        for res in results:
            self.assertTrue(res["success"], res.get("error"))

        # Inspect database rows
        rows = conexion._execute(
            "SELECT id_comando, accion, estado, creado_en FROM dispositivo_comandos WHERE torre_id=1 ORDER BY creado_en DESC, id_comando DESC",
            fetchall=True,
        )
        self.assertEqual(len(rows), 4)

        # Exactly 1 command must be 'pending'
        pending_rows = [r for r in rows if r["estado"] == "pending"]
        superseded_rows = [r for r in rows if r["estado"] == "superseded"]

        self.assertEqual(len(pending_rows), 1)
        self.assertEqual(len(superseded_rows), 3)

        # The pending command matches the query result deterministically
        active = mobile_service.get_active_command(1)
        self.assertEqual(active["id"], pending_rows[0]["id_comando"])
        self.assertEqual(active["status"], "pending")

    def test_expired_and_superseded_commands_cannot_be_acked(self):
        """Expired or superseded commands reject ACKs and cannot be executed."""
        # 1. Test expiration: command with 1 second TTL
        cmd_exp = mobile_service.create_pump_command(1, "on", ttl_sec=1)
        time.sleep(2.1)

        # Polling recognizes it as expired
        active = mobile_service.get_active_command(1)
        self.assertEqual(active["status"], "expired")

        # Attempt to ACK an expired command is rejected
        ack_res = mobile_service.record_command_ack(1, cmd_exp["id"], "executed")
        self.assertIsNone(ack_res)

        # 2. Test superseded: cmd_prev is superseded by cmd_new
        cmd_prev = mobile_service.create_pump_command(1, "on", ttl_sec=60)
        self.assertEqual(cmd_prev["status"], "pending")

        cmd_new = mobile_service.create_pump_command(1, "off", ttl_sec=60)
        self.assertEqual(cmd_new["status"], "pending")

        # cmd_prev is now superseded in DB
        prev_row = conexion._execute(
            "SELECT estado FROM dispositivo_comandos WHERE id_comando=%s",
            (cmd_prev["id"],),
            fetchone=True,
        )
        self.assertEqual(prev_row["estado"], "superseded")

        # Attempt to ACK superseded cmd_prev is rejected
        ack_superseded = mobile_service.record_command_ack(1, cmd_prev["id"], "executed")
        self.assertIsNone(ack_superseded)

        # cmd_new can be ACKed normally
        ack_new = mobile_service.record_command_ack(1, cmd_new["id"], "executed")
        self.assertIsNotNone(ack_new)
        self.assertEqual(ack_new["status"], "executed")

    def test_multi_tower_isolation_rejects_foreign_ack(self):
        """Tower B cannot ACK or alter commands belonging to Tower A."""
        # Tower 1 command
        cmd1 = mobile_service.create_pump_command(1, "on", ttl_sec=60)

        # Tower 2 command
        cmd2 = mobile_service.create_pump_command(2, "off", ttl_sec=60)

        # Tower 2 attempts to ACK Tower 1's command -> Rejected
        foreign_ack = mobile_service.record_command_ack(2, cmd1["id"], "executed")
        self.assertIsNone(foreign_ack)

        # Verify Tower 1 command is still pending
        row1 = conexion._execute(
            "SELECT estado FROM dispositivo_comandos WHERE id_comando=%s",
            (cmd1["id"],),
            fetchone=True,
        )
        self.assertEqual(row1["estado"], "pending")

        # Tower 1 legitimately ACKs its command -> Accepted
        legit_ack = mobile_service.record_command_ack(1, cmd1["id"], "executed")
        self.assertIsNotNone(legit_ack)
        self.assertEqual(legit_ack["status"], "executed")

        # Verify Tower 2 command was not touched and is still pending
        row2 = conexion._execute(
            "SELECT estado FROM dispositivo_comandos WHERE id_comando=%s",
            (cmd2["id"],),
            fetchone=True,
        )
        self.assertEqual(row2["estado"], "pending")

    def test_persistence_after_restart_without_reexecution_of_expired(self):
        """Simulate worker restart / connection recycling.

        Expired commands are persisted and never served as executable pending commands.
        """
        # Create an expired command and an active pending command
        cmd_expired = mobile_service.create_pump_command(1, "on", ttl_sec=1)
        time.sleep(1.2)

        # Simulate restart: reload configuration and query from a fresh connection
        cfg = dict(conexion.MYSQL_CONFIG)
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_worker_poll_command, args=(cfg, 1, q))
        p.start()
        p.join(timeout=10)
        res = q.get(timeout=2)
        self.assertTrue(res["success"], res.get("error"))

        # The command is returned as expired, never pending
        polled = res["cmd"]
        self.assertEqual(polled["id"], cmd_expired["id"])
        self.assertEqual(polled["status"], "expired")


if __name__ == "__main__":
    multiprocessing.set_start_method("fork", force=True)
    unittest.main()
