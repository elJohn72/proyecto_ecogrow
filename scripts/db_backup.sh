#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

MYSQL_DATABASE="${MYSQL_DATABASE:-ecogrow_mysql}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_UNIX_SOCKET="${MYSQL_UNIX_SOCKET:-}"
MYSQL_USE_SOCKET="${MYSQL_USE_SOCKET:-false}"

BACKUP_DIR="${1:-$ROOT_DIR/backups/mysql}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
OUTPUT_FILE="$BACKUP_DIR/${MYSQL_DATABASE}_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

DUMP_CMD=(mysqldump "--user=$MYSQL_USER" "--single-transaction" "--routines" "--triggers" "$MYSQL_DATABASE")

case "${MYSQL_USE_SOCKET,,}" in
  1|true|yes|on)
    if [ -n "$MYSQL_UNIX_SOCKET" ]; then
      DUMP_CMD+=("--socket=$MYSQL_UNIX_SOCKET")
    else
      DUMP_CMD+=("--host=$MYSQL_HOST" "--port=$MYSQL_PORT")
    fi
    ;;
  *)
    DUMP_CMD+=("--host=$MYSQL_HOST" "--port=$MYSQL_PORT")
    ;;
esac

if [ -n "$MYSQL_PASSWORD" ]; then
  DUMP_CMD+=("--password=$MYSQL_PASSWORD")
fi

"${DUMP_CMD[@]}" > "$OUTPUT_FILE"
cp "$OUTPUT_FILE" "$BACKUP_DIR/latest.sql"

printf 'Backup creado en %s\n' "$OUTPUT_FILE"
printf 'Copia estable en %s\n' "$BACKUP_DIR/latest.sql"
