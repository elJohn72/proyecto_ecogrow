#!/usr/bin/env python3
"""Herramienta de migración idempotente de identidades antiguas para EcoGrow 2.0.

Detecta y actualiza identificadores provisionales o placeholders de prototipo
(p. ej. 'TORRE-001', 'EG-TORRE-01', 'DUMMY') en la base de datos (dispositivos_iot
y torres), transformándolos en su código canónico derivado de la MAC real del hardware
(formato EG-TORRE-<HEX>), respetando asignaciones de usuario y telemetría existente.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

PLACEHOLDER_CODES = {
    "TORRE-001",
    "EG-TORRE-01",
    "DUMMY",
    "PRUEBA",
    "TEST",
    "IDENTIFICADOR_TECNICO",
}


def is_placeholder_code(code: str | None) -> bool:
    if not code:
        return True
    c = str(code).strip().upper()
    if len(c) < 3 or len(c) > 64:
        return True
    return c in PLACEHOLDER_CODES


def derive_canonical_code(mac: str) -> str:
    clean_mac = "".join(c for c in mac if c in "0123456789ABCDEFabcdef").upper()
    if len(clean_mac) != 12:
        raise ValueError(f"Dirección MAC inválida: '{mac}' (debe contener 12 caracteres hexadecimales)")
    return f"EG-TORRE-{clean_mac[-6:]}"


def audit_identities(conn_func=None) -> list[dict[str, Any]]:
    """Inspecciona la base de datos y lista dispositivos con códigos no canónicos o de ejemplo."""
    try:
        from Conexión.conexion import _connect, create_mysql_tables
    except ImportError:
        raise RuntimeError("No se pudo importar el módulo de conexión a la base de datos.")

    create_mysql_tables()
    conn = conn_func() if conn_func else _connect(include_database=True)
    results = []

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id_dispositivo, codigo_torre, mac, estado, reclamado_por FROM dispositivos_iot")
            rows = cursor.fetchall() or []

            for row in rows:
                code = (row.get("codigo_torre") or "").strip().upper()
                mac = (row.get("mac") or "").strip()
                is_placeholder = is_placeholder_code(code)

                item = {
                    "id_dispositivo": row["id_dispositivo"],
                    "current_code": code,
                    "mac": mac,
                    "estado": row.get("estado"),
                    "reclamado_por": row.get("reclamado_por"),
                    "is_placeholder": is_placeholder,
                    "canonical_code": None,
                    "action": "OK",
                }

                if is_placeholder:
                    try:
                        canon = derive_canonical_code(mac)
                        item["canonical_code"] = canon
                        item["action"] = "MIGRATE_TO_CANONICAL"
                    except Exception as err:
                        item["action"] = f"REQUIRES_WORKSHOP: {err}"
                else:
                    item["canonical_code"] = code

                results.append(item)
    finally:
        conn.close()

    return results


def apply_migrations(dry_run: bool = True, conn_func=None) -> dict[str, Any]:
    """Aplica la migración de códigos placeholder a códigos canónicos en dispositivos_iot y torres."""
    try:
        from Conexión.conexion import _connect, create_mysql_tables
    except ImportError:
        raise RuntimeError("No se pudo importar el módulo de conexión a la base de datos.")

    create_mysql_tables()
    conn = conn_func() if conn_func else _connect(include_database=True)

    summary = {
        "dry_run": dry_run,
        "total_checked": 0,
        "migrated": 0,
        "skipped_canonical": 0,
        "requires_workshop": 0,
        "details": [],
    }

    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id_dispositivo, codigo_torre, mac, estado, reclamado_por FROM dispositivos_iot FOR UPDATE")
            rows = cursor.fetchall() or []
            summary["total_checked"] = len(rows)

            for row in rows:
                code = (row.get("codigo_torre") or "").strip().upper()
                mac = (row.get("mac") or "").strip()

                if not is_placeholder_code(code):
                    summary["skipped_canonical"] += 1
                    continue

                try:
                    canon_code = derive_canonical_code(mac)
                except Exception as err:
                    summary["requires_workshop"] += 1
                    summary["details"].append({
                        "id_dispositivo": row["id_dispositivo"],
                        "code": code,
                        "error": str(err),
                        "status": "FAILED",
                    })
                    continue

                # Verificar si ya existe otro dispositivo con ese código canónico
                cursor.execute(
                    "SELECT id_dispositivo FROM dispositivos_iot WHERE codigo_torre = %s AND id_dispositivo != %s",
                    (canon_code, row["id_dispositivo"]),
                )
                conflict = cursor.fetchone()
                if conflict:
                    summary["requires_workshop"] += 1
                    summary["details"].append({
                        "id_dispositivo": row["id_dispositivo"],
                        "code": code,
                        "conflict_with_id": conflict["id_dispositivo"],
                        "status": "CONFLICT",
                    })
                    continue

                if not dry_run:
                    # Actualizar en dispositivos_iot
                    cursor.execute(
                        "UPDATE dispositivos_iot SET codigo_torre = %s WHERE id_dispositivo = %s",
                        (canon_code, row["id_dispositivo"]),
                    )

                    # Actualizar en torres conservando usuario_id y telemetría
                    cursor.execute(
                        "UPDATE torres SET codigo_torre = %s WHERE codigo_torre = %s",
                        (canon_code, code),
                    )

                summary["migrated"] += 1
                summary["details"].append({
                    "id_dispositivo": row["id_dispositivo"],
                    "old_code": code,
                    "new_code": canon_code,
                    "mac": mac,
                    "status": "MIGRATED" if not dry_run else "PROPOSED",
                })

        if not dry_run:
            conn.commit()
        else:
            conn.rollback()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return summary


def main():
    parser = argparse.ArgumentParser(description="Migración idempotente de identidades antiguas EcoGrow 2.0")
    parser.add_argument("--audit", action="store_true", help="Auditar dispositivos e imprimir diagnóstico sin escribir.")
    parser.add_argument("--apply", action="store_true", help="Aplicar la migración a la base de datos.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simular la migración sin escribir (por defecto).")

    args = parser.parse_args()

    if args.audit:
        print("=== Auditoría de Identidades en Base de Datos EcoGrow ===")
        items = audit_identities()
        if not items:
            print("No hay dispositivos registrados en la base de datos.")
            return

        for it in items:
            print(f"- ID {it['id_dispositivo']}: Actual='{it['current_code']}', MAC='{it['mac']}', Estado='{it['estado']}', Acción={it['action']}, Canónico='{it['canonical_code']}'")
        return

    is_apply = args.apply
    is_dry = not is_apply

    mode_str = "APLICACIÓN REAL" if is_apply else "SIMULACIÓN (DRY-RUN)"
    print(f"=== Ejecutando Migración de Identidades ({mode_str}) ===")
    res = apply_migrations(dry_run=is_dry)

    print(f"Total dispositivos revisados : {res['total_checked']}")
    print(f"Ya canónicos (sin cambio)    : {res['skipped_canonical']}")
    print(f"Migraciones {'aplicadas' if is_apply else 'propuestas'}: {res['migrated']}")
    print(f"Requieren taller manual      : {res['requires_workshop']}")

    for d in res["details"]:
        print(f"  * {d}")

    if is_dry and res["migrated"] > 0:
        print("\nPara aplicar las migraciones a la base de datos, ejecuta: python3 tools/migrate_identities.py --apply")


if __name__ == "__main__":
    main()
