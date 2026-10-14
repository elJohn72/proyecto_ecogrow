#!/usr/bin/env python3
"""Migración idempotente de identidades antiguas de EcoGrow 2.0.

Actualiza placeholders de prototipo en dispositivos_iot.codigo_torre y en
torres.codigo_unico. Conserva el id, el usuario, el historial y la
configuración porque esas tablas referencian id_torre, no el código.
No modifica la NVS del ESP32: el cambio de hardware es un paso de taller
posterior y recuperable.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Callable

PLACEHOLDER_CODES = {
    "TORRE-001",
    "EG-TORRE-01",
    "DUMMY",
    "PRUEBA",
    "TEST",
    "IDENTIFICADOR_TECNICO",
}


def _ensure_repo_on_path() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def is_placeholder_code(code: str | None) -> bool:
    if not code:
        return True
    normalized = str(code).strip().upper()
    if len(normalized) < 3 or len(normalized) > 64:
        return True
    return normalized in PLACEHOLDER_CODES


def derive_canonical_code(mac: str) -> str:
    clean_mac = "".join(c for c in mac if c in "0123456789ABCDEFabcdef").upper()
    if len(clean_mac) != 12:
        raise ValueError(f"Dirección MAC inválida: '{mac}' (debe contener 12 caracteres hexadecimales)")
    return f"EG-TORRE-{clean_mac[-6:]}"


def _normalize_mac(mac: str) -> str:
    clean_mac = "".join(c for c in mac if c in "0123456789ABCDEFabcdef").upper()
    if len(clean_mac) != 12:
        raise ValueError(f"Dirección MAC inválida: '{mac}'")
    return ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))


def _open_connection(conn_func=None):
    _ensure_repo_on_path()
    try:
        from Conexión.conexion import _connect, create_mysql_tables
    except ImportError as exc:
        raise RuntimeError("No se pudo importar el módulo de conexión a la base de datos.") from exc
    create_mysql_tables()
    return conn_func() if conn_func else _connect(include_database=True)


def audit_identities(conn_func=None) -> list[dict[str, Any]]:
    """Lista dispositivos con código placeholder. No escribe."""
    conn = _open_connection(conn_func)
    results = []
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT id_dispositivo, codigo_torre, mac, estado, reclamado_por FROM dispositivos_iot"
            )
            rows = cursor.fetchall() or []
            for row in rows:
                code = (row.get("codigo_torre") or "").strip().upper()
                mac = (row.get("mac") or "").strip()
                placeholder = is_placeholder_code(code)
                item = {
                    "id_dispositivo": row["id_dispositivo"],
                    "current_code": code,
                    "mac": mac,
                    "estado": row.get("estado"),
                    "reclamado_por": row.get("reclamado_por"),
                    "is_placeholder": placeholder,
                    "canonical_code": None,
                    "action": "OK",
                }
                if placeholder:
                    try:
                        item["canonical_code"] = derive_canonical_code(mac)
                        item["action"] = "MIGRATE_TO_CANONICAL"
                    except Exception as err:
                        item["action"] = f"REQUIRES_WORKSHOP: {err}"
                else:
                    item["canonical_code"] = code
                results.append(item)
    finally:
        conn.close()
    return results


def _lock_conflicts(cursor, device_id: int, old_code: str, canonical: str) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT id_dispositivo
        FROM dispositivos_iot
        WHERE codigo_torre = %s AND id_dispositivo != %s
        FOR UPDATE
        """,
        (canonical, device_id),
    )
    device_conflict = cursor.fetchone()
    if device_conflict:
        return {
            "kind": "dispositivos_iot",
            "conflict_with_id": device_conflict["id_dispositivo"],
        }

    cursor.execute(
        "SELECT id_torre, usuario_id FROM torres WHERE codigo_unico = %s FOR UPDATE",
        (canonical,),
    )
    tower_conflict = cursor.fetchone()
    if tower_conflict and old_code != canonical:
        return {
            "kind": "torres",
            "conflict_with_id": tower_conflict["id_torre"],
            "usuario_id": tower_conflict.get("usuario_id"),
        }
    return None


def apply_migrations(
    dry_run: bool = True,
    conn_func=None,
    only_mac: str | None = None,
    before_commit: Callable | None = None,
) -> dict[str, Any]:
    """Migra placeholders en una transacción. dry_run no escribe.

    Un fallo antes del commit revierte dispositivos_iot y torres juntos.
    La segunda ejecución sobre códigos ya canónicos no los cambia.
    """
    conn = _open_connection(conn_func)
    summary: dict[str, Any] = {
        "dry_run": dry_run,
        "total_checked": 0,
        "migrated": 0,
        "skipped_canonical": 0,
        "requires_workshop": 0,
        "details": [],
    }
    mac_filter = _normalize_mac(only_mac) if only_mac else None

    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cursor:
            if mac_filter:
                cursor.execute(
                    """
                    SELECT id_dispositivo, codigo_torre, mac, estado, reclamado_por
                    FROM dispositivos_iot
                    WHERE mac = %s
                    FOR UPDATE
                    """,
                    (mac_filter,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id_dispositivo, codigo_torre, mac, estado, reclamado_por
                    FROM dispositivos_iot
                    FOR UPDATE
                    """
                )
            rows = cursor.fetchall() or []
            summary["total_checked"] = len(rows)
            planned: list[dict[str, Any]] = []

            for row in rows:
                code = (row.get("codigo_torre") or "").strip().upper()
                mac = (row.get("mac") or "").strip()
                if not is_placeholder_code(code):
                    summary["skipped_canonical"] += 1
                    continue
                try:
                    canonical = derive_canonical_code(mac)
                except Exception as err:
                    summary["requires_workshop"] += 1
                    summary["details"].append({
                        "id_dispositivo": row["id_dispositivo"],
                        "code": code,
                        "error": str(err),
                        "status": "FAILED",
                    })
                    continue

                conflict = _lock_conflicts(cursor, row["id_dispositivo"], code, canonical)
                if conflict:
                    summary["requires_workshop"] += 1
                    summary["details"].append({
                        "id_dispositivo": row["id_dispositivo"],
                        "code": code,
                        "canonical_code": canonical,
                        "conflict_with_id": conflict["conflict_with_id"],
                        "conflict_table": conflict["kind"],
                        "status": "CONFLICT",
                    })
                    continue

                cursor.execute(
                    "SELECT id_torre, usuario_id FROM torres WHERE codigo_unico = %s FOR UPDATE",
                    (code,),
                )
                owned_tower = cursor.fetchone()
                planned.append({
                    "id_dispositivo": row["id_dispositivo"],
                    "old_code": code,
                    "new_code": canonical,
                    "mac": mac,
                    "estado": row.get("estado"),
                    "reclamado_por": row.get("reclamado_por"),
                    "id_torre": owned_tower["id_torre"] if owned_tower else None,
                    "usuario_id": owned_tower["usuario_id"] if owned_tower else None,
                })

            if dry_run:
                conn.rollback()
                summary["migrated"] = len(planned)
                for item in planned:
                    summary["details"].append({**item, "status": "PROPOSED"})
                return summary

            if not planned:
                conn.rollback()
                return summary

            for item in planned:
                cursor.execute(
                    """
                    UPDATE dispositivos_iot
                    SET codigo_torre = %s
                    WHERE id_dispositivo = %s AND codigo_torre = %s
                    """,
                    (item["new_code"], item["id_dispositivo"], item["old_code"]),
                )
                if isinstance(cursor.rowcount, int) and cursor.rowcount != 1:
                    raise RuntimeError(
                        "La fila de dispositivos_iot no se actualizó; la transacción se revierte."
                    )
                cursor.execute(
                    "UPDATE torres SET codigo_unico = %s WHERE codigo_unico = %s",
                    (item["new_code"], item["old_code"]),
                )
                summary["migrated"] += 1
                summary["details"].append({**item, "status": "MIGRATED"})

            if before_commit is not None:
                before_commit(cursor)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return summary


def revert_code_migration(
    mac: str,
    old_code: str,
    new_code: str,
    conn_func=None,
) -> dict[str, Any]:
    """Devuelve el código anterior si esta MAC sigue en el código nuevo y el anterior está libre.

    Sirve cuando el hardware no llegó a aceptar el código nuevo. No borra usuario,
    id, token ni historial.
    """
    mac_norm = _normalize_mac(mac)
    old_norm = (old_code or "").strip().upper()
    new_norm = (new_code or "").strip().upper()
    if not old_norm or not new_norm or old_norm == new_norm:
        return {"reverted": False, "reason": "sin_codigo_anterior_restaurable"}

    conn = _open_connection(conn_func)
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT id_dispositivo, codigo_torre, reclamado_por FROM dispositivos_iot WHERE mac = %s FOR UPDATE",
                (mac_norm,),
            )
            device = cursor.fetchone()
            if not device:
                conn.rollback()
                return {"reverted": False, "reason": "dispositivo_ausente"}
            if device["codigo_torre"].strip().upper() == old_norm:
                conn.rollback()
                return {"reverted": False, "reason": "ya_estaba_en_codigo_anterior"}
            if device["codigo_torre"].strip().upper() != new_norm:
                conn.rollback()
                return {"reverted": False, "reason": "codigo_actual_no_coincide"}

            conflict = _lock_conflicts(cursor, device["id_dispositivo"], new_norm, old_norm)
            if conflict:
                conn.rollback()
                return {"reverted": False, "reason": "conflicto", "conflict": conflict}

            cursor.execute(
                """
                UPDATE dispositivos_iot
                SET codigo_torre = %s
                WHERE id_dispositivo = %s AND codigo_torre = %s
                """,
                (old_norm, device["id_dispositivo"], new_norm),
            )
            if isinstance(cursor.rowcount, int) and cursor.rowcount != 1:
                raise RuntimeError("No se pudo revertir dispositivos_iot.")
            cursor.execute(
                "UPDATE torres SET codigo_unico = %s WHERE codigo_unico = %s",
                (old_norm, new_norm),
            )
            conn.commit()
            return {
                "reverted": True,
                "id_dispositivo": device["id_dispositivo"],
                "reclamado_por": device.get("reclamado_por"),
                "old_code": old_norm,
                "new_code": new_norm,
            }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migración idempotente de identidades antiguas EcoGrow 2.0")
    parser.add_argument("--audit", action="store_true", help="Auditar dispositivos e imprimir diagnóstico sin escribir.")
    parser.add_argument("--apply", action="store_true", help="Aplicar la migración a la base de datos.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simular la migración sin escribir (por defecto).")
    parser.add_argument("--mac", help="Limitar la migración a una MAC física.")

    args = parser.parse_args()

    if args.audit:
        print("=== Auditoría de Identidades en Base de Datos EcoGrow ===")
        items = audit_identities()
        if not items:
            print("No hay dispositivos registrados en la base de datos.")
            return
        for item in items:
            print(
                f"- ID {item['id_dispositivo']}: Actual='{item['current_code']}', "
                f"MAC='{item['mac']}', Estado='{item['estado']}', Acción={item['action']}, "
                f"Canónico='{item['canonical_code']}'"
            )
        return

    is_apply = args.apply
    is_dry = not is_apply
    mode_str = "APLICACIÓN REAL" if is_apply else "SIMULACIÓN (DRY-RUN)"
    print(f"=== Ejecutando Migración de Identidades ({mode_str}) ===")
    result = apply_migrations(dry_run=is_dry, only_mac=args.mac)

    print(f"Total dispositivos revisados : {result['total_checked']}")
    print(f"Ya canónicos (sin cambio)    : {result['skipped_canonical']}")
    print(f"Migraciones {'aplicadas' if is_apply else 'propuestas'}: {result['migrated']}")
    print(f"Requieren taller manual      : {result['requires_workshop']}")
    for detail in result["details"]:
        printable = {key: value for key, value in detail.items() if key != "mac"}
        print(f"  * {printable}")

    if is_dry and result["migrated"] > 0:
        print("\nPara aplicar las migraciones a la base de datos, ejecuta: python3 tools/migrate_identities.py --apply")


if __name__ == "__main__":
    main()
