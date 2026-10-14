#!/bin/bash
# Encola el redeploy de ecogrow-app en Coolify y espera el resultado.
# No abre puertos administrativos y no imprime secretos.
set -euo pipefail

APP_UUID="w3bmo8epk9iedi7gkqchdpru"

php_code='$app = App\Models\Application::where("uuid", "w3bmo8epk9iedi7gkqchdpru")->first(); if (!$app) { echo json_encode(["status" => "missing"]); } else { $deploymentUuid = new_public_id(); $result = queue_application_deployment(application: $app, deployment_uuid: $deploymentUuid, force_rebuild: false, is_api: true); echo json_encode(["status" => $result["status"] ?? null, "message" => $result["message"] ?? null, "deployment_uuid" => $deploymentUuid]); }'

raw=$(docker exec coolify php artisan tinker --execute="$php_code")
line=$(printf '%s\n' "$raw" | grep -E '^\{' | tail -n 1 || true)
if [ -z "$line" ]; then
  echo "ecogrow-deploy no devolvió un estado JSON"
  exit 1
fi
echo "$line"

status=$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status") or "")')
uuid=$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("deployment_uuid") or "")')

if [ "$status" = "skipped" ]; then
  echo "ecogrow-deploy skipped"
  exit 0
fi
if [ "$status" != "queued" ]; then
  echo "ecogrow-deploy not queued"
  exit 1
fi
if ! printf '%s' "$uuid" | grep -Eq '^[a-z0-9]+$'; then
  echo "ecogrow-deploy uuid inválido"
  exit 1
fi

for _ in $(seq 1 40); do
  row=$(docker exec coolify-db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tA -c \"SELECT status || ' ' || left(coalesce(commit,''),12) FROM application_deployment_queues WHERE deployment_uuid='${uuid}';\"")
  echo "ecogrow-deploy ${row}"
  case "$row" in
    finished*) exit 0 ;;
    failed*|cancelled*) exit 1 ;;
  esac
  sleep 10
done

echo "ecogrow-deploy timeout"
exit 1
