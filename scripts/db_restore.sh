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
INPUT_FILE="${1:-$ROOT_DIR/backups/mysql/latest.sql}"

if [ ! -f "$INPUT_FILE" ]; then
  printf 'No existe el archivo de respaldo: %s\n' "$INPUT_FILE" >&2
  exit 1
fi

RESTORE_CMD=(mysql "--user=$MYSQL_USER" "$MYSQL_DATABASE")

case "${MYSQL_USE_SOCKET,,}" in
  1|true|yes|on)
    if [ -n "$MYSQL_UNIX_SOCKET" ]; then
      RESTORE_CMD+=("--socket=$MYSQL_UNIX_SOCKET")
    else
      RESTORE_CMD+=("--host=$MYSQL_HOST" "--port=$MYSQL_PORT")
    fi
    ;;
  *)
    RESTORE_CMD+=("--host=$MYSQL_HOST" "--port=$MYSQL_PORT")
    ;;
esac

if [ -n "$MYSQL_PASSWORD" ]; then
  RESTORE_CMD+=("--password=$MYSQL_PASSWORD")
fi

"${RESTORE_CMD[@]}" < "$INPUT_FILE"

printf 'Base restaurada desde %s\n' "$INPUT_FILE"
