#!/usr/bin/env bash
set -euo pipefail

# Script de despliegue controlado de EcoGrow en VPS kv2
# Uso: ./scripts/deploy_vps.sh

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../deploy" && pwd)"
ENV_FILE="${DEPLOY_DIR}/.env"

echo "=== Despliegue de EcoGrow en VPS kv2 ==="

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: No se encontró el archivo $ENV_FILE."
    echo "Copia deploy/env.example a deploy/.env y define las credenciales."
    exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker no está instalado."; exit 1; }

echo "1. Comprobando configuración de Docker Compose..."
docker compose -f "${DEPLOY_DIR}/docker-compose.yml" --env-file "$ENV_FILE" config >/dev/null

echo "2. Descargando imágenes base..."
docker compose -f "${DEPLOY_DIR}/docker-compose.yml" --env-file "$ENV_FILE" pull --ignore-buildable || true

echo "3. Compilando y levantando contenedores aislados..."
docker compose -f "${DEPLOY_DIR}/docker-compose.yml" --env-file "$ENV_FILE" up -d --build --remove-orphans

echo "4. Esperando verificación de salud (health check)..."
MAX_RETRIES=20
COUNT=0
HEALTHY=false

while [[ $COUNT -lt $MAX_RETRIES ]]; do
    APP_STATUS=$(docker compose -f "${DEPLOY_DIR}/docker-compose.yml" ps app --format '{{.Health}}' 2>/dev/null || true)
    if [[ "$APP_STATUS" == "healthy" ]]; then
        HEALTHY=true
        break
    fi
    echo "Esperando que el servicio 'app' esté saludable (estado actual: '${APP_STATUS:-iniciando}')... ($((COUNT+1))/$MAX_RETRIES)"
    sleep 3
    COUNT=$((COUNT+1))
done

if [[ "$HEALTHY" = true ]]; then
    echo "✅ Despliegue exitoso. EcoGrow está en ejecución y saludable."
    docker compose -f "${DEPLOY_DIR}/docker-compose.yml" ps
else
    echo "❌ ERROR: El contenedor no alcanzó estado saludable."
    echo "=== Logs del servicio app ==="
    docker compose -f "${DEPLOY_DIR}/docker-compose.yml" logs --tail=50 app
    echo "Iniciando rollback o parada de emergencia..."
    docker compose -f "${DEPLOY_DIR}/docker-compose.yml" stop app proxy || true
    exit 1
fi
