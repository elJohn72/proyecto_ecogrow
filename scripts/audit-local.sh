#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-5050}"
BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT}}"
OUT_DIR="${ROOT}/docs/auditoria"
mkdir -p "$OUT_DIR"

export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v squirrel >/dev/null 2>&1; then
  echo "Instala SquirrelScan: curl -fsSL https://squirrelscan.com/install.sh | bash"
  exit 1
fi

echo "==> Auditoría surface en ${BASE_URL}"
squirrel audit "${BASE_URL}" -C surface -m 80 --refresh --format llm \
  -o "${OUT_DIR}/squirrel-report-surface-latest.txt"

echo "==> Reporte guardado en ${OUT_DIR}/squirrel-report-surface-latest.txt"
