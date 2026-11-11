#!/usr/bin/env bash
# Tráfico simulado para que las gráficas de Grafana tengan movimiento.
# Uso: deploy/kind/traffic.sh [http://localhost:8090]   (Ctrl+C para detener)
set -uo pipefail

BASE_URL="${1:-http://localhost:8090}"
TOPICS=('"Mercados"' '"Economía"' '"Finanzas personales"' '"Tecnología"')
NAMES=("Ana López" "Luis Pérez" "María García" "Carlos Ruiz" "Sofía Torres" "Diego Ramírez")
EMAILS=()
count=0

request() {
  curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$@" || printf '000'
}

echo "Generando tráfico contra ${BASE_URL} (Ctrl+C para detener)"
while true; do
  roll=$((RANDOM % 10))
  if (( roll < 2 || ${#EMAILS[@]} == 0 )); then
    name="${NAMES[RANDOM % ${#NAMES[@]}]}"
    email="usuario$((RANDOM % 500))@example.com"
    topic="${TOPICS[RANDOM % ${#TOPICS[@]}]}"
    code=$(request -X POST "${BASE_URL}/api/subscriptions" -H 'Content-Type: application/json' \
      -d "{\"name\":\"${name}\",\"email\":\"${email}\",\"password\":\"demo-password\",\"topics\":[${topic}]}")
    EMAILS+=("$email")
    label="POST /api/subscriptions"
  elif (( roll < 8 )); then
    email="${EMAILS[RANDOM % ${#EMAILS[@]}]}"
    code=$(request "${BASE_URL}/api/dashboard?email=${email}")
    label="GET  /api/dashboard"
  elif (( roll < 9 )); then
    code=$(request "${BASE_URL}/api/dashboard?email=nadie$((RANDOM))@example.com")
    label="GET  /api/dashboard (cuenta inexistente)"
  else
    code=$(request "${BASE_URL}/api/health")
    label="GET  /api/health"
  fi
  count=$((count + 1))
  printf '%5d  %s  %s\n' "$count" "$code" "$label"
  sleep 0.$((1 + RANDOM % 3))
done
