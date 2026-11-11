#!/usr/bin/env bash
# Smoke test contra una Finance Platform en ejecución.
# Uso: tests/smoke/smoke.sh [http://localhost:8082]
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:8082}}"
EMAIL="smoke-$(date +%s)@example.com"

check() {
  local description="$1"
  shift
  if "$@" >/dev/null; then
    echo "✓ ${description}"
  else
    echo "✗ ${description}" >&2
    exit 1
  fi
}

wait_for() {
  for _ in $(seq 1 30); do
    if curl -fsS "$1" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "✗ ${1} no respondió a tiempo" >&2
  exit 1
}

echo "Smoke test contra ${BASE_URL}"
wait_for "${BASE_URL}/api/health"

check "Frontend saludable" curl -fsS "${BASE_URL}/health/frontend"
check "Página principal" curl -fsS "${BASE_URL}/"
check "Página de suscripción" curl -fsS "${BASE_URL}/subscribe.html"
check "API conectada a PostgreSQL" bash -c "curl -fsS '${BASE_URL}/api/health' | grep -q '\"database\":\"connected\"'"
check "Crear suscripción" curl -fsS -X POST "${BASE_URL}/api/subscriptions" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Smoke Test\",\"email\":\"${EMAIL}\",\"password\":\"smoke-test-123\",\"topics\":[\"Mercados\"]}"
check "Leer dashboard" bash -c "curl -fsS '${BASE_URL}/api/dashboard?email=${EMAIL}' | grep -q 'finance_plus'"
check "Métricas Prometheus" bash -c "curl -fsS '${BASE_URL}/api/metrics' | grep -q finance_api_requests_total"

echo "Smoke test completado"
