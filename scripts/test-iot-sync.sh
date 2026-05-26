#!/usr/bin/env bash
# Prueba rapida de POST /api/iot/sync (sin ESP32)
set -euo pipefail

BASE_URL="${ECOGROW_BASE_URL:-http://127.0.0.1:5000}"
TOKEN="${ECOGROW_SENSOR_API_TOKEN:-}"
TORRE="${TORRE_CODIGO:-ECO-TORRE-001}"
RELE="${RELE_PRINCIPAL:-false}"

if [[ -z "$TOKEN" ]]; then
  echo "Define ECOGROW_SENSOR_API_TOKEN" >&2
  exit 1
fi

curl -sS -X POST "${BASE_URL}/api/iot/sync" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: ${TOKEN}" \
  -d "{\"torre_codigo\":\"${TORRE}\",\"dispositivo\":\"curl_test\",\"rele_principal\":${RELE}}" \
  | python3 -m json.tool
