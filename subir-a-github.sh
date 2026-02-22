#!/bin/bash
# Script para crear el repo en GitHub y subir el código
set -e
cd "$(dirname "$0")"

echo "Comprobando sesión de GitHub..."
if ! gh auth status &>/dev/null; then
  echo "No estás logueado en GitHub. Ejecuta primero: gh auth login --web"
  exit 1
fi

echo "Creando repositorio 'proyecto_ecogrow' en GitHub y subiendo código..."
gh repo create proyecto_ecogrow --public --source=. --remote=origin --push

echo ""
echo "Listo. Tu proyecto está en: https://github.com/$(gh api user -q .login)/proyecto_ecogrow"
