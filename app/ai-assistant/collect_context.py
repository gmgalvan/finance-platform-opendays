"""Recolecta el contexto de un incidente. Solo lectura.

Consulta lo mismo que revisaría una persona siguiendo el runbook:
alertas y métricas (Prometheus), trazas con error (Jaeger) y el estado de
Kubernetes (deployments, historial de despliegues, pods, eventos y logs).

Nada de lo que hace este módulo cambia el sistema: solo usa GET y
`kubectl get/logs/rollout history`.

Uso:
    python collect_context.py > contexto.json
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

PROMETHEUS_URL = "http://localhost:9090"
JAEGER_URL = "http://localhost:16686"
NAMESPACE = "finance"
DEPLOYMENTS = ["api", "frontend", "market-data"]
USER_TRAFFIC = 'path!~"/metrics|/health"'

PROMETHEUS_QUERIES = {
    "disponibilidad_5m_pct": "sli:availability:ratio_rate5m * 100",
    "consumo_presupuesto_5m": "slo:availability:burn_rate5m",
    "consumo_presupuesto_1m": "slo:availability:burn_rate1m",
    "presupuesto_restante_1h_pct": "slo:availability:error_budget_remaining1h * 100",
    "latencia_bajo_500ms_5m_pct": "sli:latency:ratio_rate5m * 100",
    "errores_5xx_por_endpoint_req_s": (
        f'sum by (path, status) (rate(finance_api_requests_total{{{USER_TRAFFIC}, status=~"5.."}}[5m]))'
    ),
    "trafico_por_endpoint_req_s": f"sum by (path) (rate(finance_api_requests_total{{{USER_TRAFFIC}}}[5m]))",
    "latencia_p95_por_endpoint_s": (
        "histogram_quantile(0.95, sum by (le, path) "
        f"(rate(finance_api_request_duration_seconds_bucket{{{USER_TRAFFIC}}}[5m])))"
    ),
    "errores_market_data_req_s": (
        'sum by (status) (rate(market_data_requests_total{path="/quotes"}[5m]))'
    ),
    "pods_activos_por_version": "count by (app, version) (up{job=\"finance-pods\"} == 1)",
}


def _round(value: str) -> float:
    number = float(value)
    return round(number, 3) if number == number else None  # NaN → None


def prometheus(client: httpx.Client) -> dict:
    alerts = client.get(f"{PROMETHEUS_URL}/api/v1/alerts").json()["data"]["alerts"]
    result = {
        "alertas": [
            {
                "nombre": alert["labels"]["alertname"],
                "estado": alert["state"],
                "severidad": alert["labels"].get("severity"),
                "desde": alert.get("activeAt"),
                "resumen": alert["annotations"].get("summary"),
            }
            for alert in alerts
        ],
        "metricas": {},
        # Las consultas exactas, para que el análisis use nombres de métricas reales.
        "consultas_promql": PROMETHEUS_QUERIES,
    }
    for name, query in PROMETHEUS_QUERIES.items():
        series = client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}).json()["data"]["result"]
        result["metricas"][name] = [
            {"etiquetas": serie["metric"], "valor": _round(serie["value"][1])} for serie in series
        ]
    return result


def jaeger(client: httpx.Client, limit: int = 5, minutes: int = 10) -> dict:
    services = client.get(f"{JAEGER_URL}/api/services").json()["data"] or []
    now_us = int(time.time() * 1_000_000)
    errors = []
    seen = set()  # la misma traza aparece al buscar por cada servicio que cruza
    for service in sorted(services):
        if service == "jaeger":
            continue
        traces = client.get(
            f"{JAEGER_URL}/api/traces",
            params={
                "service": service,
                "tags": '{"error":"true"}',
                "start": now_us - minutes * 60 * 1_000_000,
                "end": now_us,
                "limit": limit,
            },
        ).json()["data"] or []
        for trace in traces:
            processes = trace["processes"]
            failing = []
            started_us = min(span["startTime"] for span in trace["spans"])
            for span in trace["spans"]:
                tags = {tag["key"]: tag["value"] for tag in span["tags"]}
                # "http send/receive" son eventos internos de ASGI: solo ruido.
                if span["operationName"].endswith(("http send", "http receive")):
                    continue
                if tags.get("error") in (True, "true"):
                    failing.append(
                        {
                            "servicio": processes[span["processID"]]["serviceName"],
                            "operacion": span["operationName"],
                            "duracion_ms": round(span["duration"] / 1000, 1),
                            "codigo_http": tags.get("http.response.status_code") or tags.get("http.status_code"),
                        }
                    )
            if failing and trace["traceID"] not in seen:
                seen.add(trace["traceID"])
                errors.append(
                    {
                        "traza": trace["traceID"],
                        "hace_segundos": round((now_us - started_us) / 1_000_000),
                        "spans_con_error": failing,
                    }
                )
    return {
        "ventana_minutos": minutes,
        "servicios": sorted(services),
        "trazas_con_error": errors[: limit * 2],
    }


def kubectl(*args: str) -> str:
    completed = subprocess.run(
        ["kubectl", "-n", NAMESPACE, *args], capture_output=True, text=True, timeout=30
    )
    return completed.stdout if completed.returncode == 0 else f"(error: {completed.stderr.strip()})"


def kubernetes() -> dict:
    deployments = json.loads(kubectl("get", "deployments", "-o", "json"))["items"]
    pods = json.loads(kubectl("get", "pods", "-o", "json"))["items"]
    events = json.loads(kubectl("get", "events", "-o", "json"))["items"]
    return {
        "deployments": [
            {
                "nombre": item["metadata"]["name"],
                "imagen": item["spec"]["template"]["spec"]["containers"][0]["image"],
                "replicas_listas": f'{item["status"].get("readyReplicas", 0)}/{item["spec"]["replicas"]}',
                # Solo variables con valor directo; las que vienen de un Secret no se envían.
                "variables": {
                    env["name"]: env["value"]
                    for env in item["spec"]["template"]["spec"]["containers"][0].get("env", [])
                    if "value" in env
                },
                "causa_del_ultimo_cambio": item["metadata"].get("annotations", {}).get(
                    "kubernetes.io/change-cause"
                ),
            }
            for item in deployments
        ],
        "historial_de_despliegues": {
            name: kubectl("rollout", "history", f"deployment/{name}").strip() for name in DEPLOYMENTS
        },
        "pods": [
            {
                "nombre": pod["metadata"]["name"],
                "fase": pod["status"]["phase"],
                "reinicios": sum(c.get("restartCount", 0) for c in pod["status"].get("containerStatuses", [])),
                "creado": pod["metadata"]["creationTimestamp"],
            }
            for pod in pods
        ],
        "eventos_recientes": [
            f'{event.get("lastTimestamp") or event.get("eventTime")} {event["reason"]} '
            f'{event["involvedObject"]["kind"]}/{event["involvedObject"]["name"]}: {event.get("message", "")}'
            for event in sorted(events, key=lambda e: e.get("lastTimestamp") or e.get("eventTime") or "")[-15:]
        ],
        "logs_recientes": {
            name: kubectl("logs", f"deployment/{name}", "--tail=15").strip().splitlines()
            for name in ("api", "market-data")
        },
    }


def collect() -> dict:
    with httpx.Client(timeout=10.0) as client:
        return {
            "recolectado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prometheus": prometheus(client),
            "jaeger": jaeger(client),
            "kubernetes": kubernetes(),
        }


if __name__ == "__main__":
    json.dump(collect(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
