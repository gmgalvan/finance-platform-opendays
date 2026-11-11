"""Genera dashboards/finance-platform.json.

Uso: python3 observability/grafana/generate_dashboard.py > observability/grafana/dashboards/finance-platform.json
"""

import json
import sys

DS = {"type": "prometheus", "uid": "prometheus"}
USER = 'path!~"/metrics|/health"'
REQ = f"finance_api_requests_total{{{USER}}}"


def target(expr, legend="", instant=False):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": "A"}
    if instant:
        t["instant"] = True
    return t


def stat(pid, title, desc, expr, unit, x, y, w=6, h=5, thresholds=None, decimals=None):
    steps = thresholds or [{"color": "green", "value": None}]
    panel = {
        "id": pid,
        "type": "stat",
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(expr)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {"mode": "absolute", "steps": steps},
                "color": {"mode": "thresholds"},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "background",
            "graphMode": "area",
            "textMode": "value",
            "justifyMode": "center",
        },
    }
    if decimals is not None:
        panel["fieldConfig"]["defaults"]["decimals"] = decimals
    return panel


def series(pid, title, desc, targets, unit, x, y, w=12, h=8, stack=False, legend_calcs=None):
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "description": desc,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 25 if stack else 10,
                    "showPoints": "never",
                    "stacking": {"mode": "normal" if stack else "none", "group": "A"},
                },
            },
            "overrides": [],
        },
        "options": {
            "legend": {
                "displayMode": "table" if legend_calcs else "list",
                "placement": "bottom",
                "calcs": legend_calcs or [],
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


panels = [
    stat(
        1,
        "Disponibilidad (5 min)",
        "Porcentaje de solicitudes de usuarios que no terminaron en error 5xx.",
        f'100 * (1 - (sum(rate({REQ[:-1]},status=~"5.."}}[5m])) or vector(0)) / sum(rate({REQ}[5m])))',
        "percent",
        0, 0,
        thresholds=[
            {"color": "red", "value": None},
            {"color": "orange", "value": 99},
            {"color": "green", "value": 99.9},
        ],
        decimals=2,
    ),
    stat(
        2,
        "Solicitudes por segundo",
        "Tráfico de usuarios hacia la API (sin probes ni Prometheus).",
        f"sum(rate({REQ}[1m]))",
        "reqps",
        6, 0,
        decimals=1,
    ),
    stat(
        3,
        "Latencia p95",
        "El 95 % de las solicitudes tarda menos que este valor.",
        f'histogram_quantile(0.95, sum by (le) (rate(finance_api_request_duration_seconds_bucket{{{USER}}}[5m])))',
        "s",
        12, 0,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "orange", "value": 0.3},
            {"color": "red", "value": 1},
        ],
        decimals=3,
    ),
    stat(
        4,
        "Suscripciones (1 h)",
        "Suscripciones creadas con éxito en la última hora.",
        'sum(increase(finance_api_requests_total{path="/api/subscriptions",status="201"}[1h]))',
        "none",
        18, 0,
        thresholds=[{"color": "blue", "value": None}],
        decimals=0,
    ),
    series(
        5,
        "Réplicas de la API por versión",
        "Pods de la API que Prometheus ve activos, agrupados por la etiqueta de la imagen. "
        "Durante un Rolling Update la versión anterior baja y la nueva sube.",
        [target('count by (version) (up{app="api"} == 1)', "{{version}}")],
        "none",
        0, 5,
        stack=True,
        legend_calcs=["lastNotNull"],
    ),
    series(
        6,
        "Solicitudes por segundo, por endpoint",
        "Tráfico de usuarios por ruta de la API.",
        [target(f"sum by (method, path) (rate({REQ}[1m]))", "{{method}} {{path}}")],
        "reqps",
        12, 5,
    ),
    series(
        7,
        "Respuestas por código HTTP",
        "2xx éxito, 4xx error del cliente (por ejemplo, cuenta inexistente), 5xx error del servidor.",
        [target(f"sum by (status) (rate({REQ}[1m]))", "{{status}}")],
        "reqps",
        0, 13,
        stack=True,
    ),
    series(
        8,
        "Latencia (p50 y p95)",
        "Tiempo de respuesta de la API.",
        [
            target(
                f"histogram_quantile(0.50, sum by (le) (rate(finance_api_request_duration_seconds_bucket{{{USER}}}[1m])))",
                "p50",
            ),
            dict(
                target(
                    f"histogram_quantile(0.95, sum by (le) (rate(finance_api_request_duration_seconds_bucket{{{USER}}}[1m])))",
                    "p95",
                ),
                refId="B",
            ),
        ],
        "s",
        12, 13,
    ),
]


def row(pid, title, y):
    return {"id": pid, "type": "row", "title": title, "collapsed": False, "panels": [],
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}}


OFFSET = 1 + 5 + 8 + 1
for panel in panels:
    panel["gridPos"]["y"] += OFFSET

slo_panels = [
    row(20, "SLO — ¿los usuarios están bien?", 0),
    stat(21, "Disponibilidad (1 h) · SLO 99 %",
         "Solicitudes de usuarios sin error 5xx en la última hora. Meta: 99 %.",
         "sli:availability:ratio_rate1h * 100", "percent", 0, 1,
         thresholds=[{"color": "red", "value": None}, {"color": "green", "value": 99}], decimals=2),
    stat(22, "Presupuesto de error restante (1 h)",
         "Con un SLO de 99 % se puede fallar el 1 %. Cuánto queda de ese margen en la última hora.",
         "slo:availability:error_budget_remaining1h * 100", "percent", 6, 1,
         thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 25}, {"color": "green", "value": 50}],
         decimals=0),
    stat(23, "Velocidad de consumo (5 m)",
         "1 = se gasta el presupuesto al ritmo permitido. Más de 5 dispara la alerta AltaTasaDeErrores.",
         "slo:availability:burn_rate5m", "short", 12, 1,
         thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}],
         decimals=1),
    stat(24, "Alertas activas",
         "Alertas de Prometheus en estado firing. Detalle en http://localhost:9093.",
         'count(ALERTS{alertstate="firing"}) or vector(0)', "none", 18, 1,
         thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 1}], decimals=0),
    series(25, "Disponibilidad vs SLO (5 m)",
           "Si la línea cae debajo del 99 %, se está gastando el presupuesto de error.",
           [target("sli:availability:ratio_rate5m * 100", "Disponibilidad"),
            dict(target("vector(99)", "SLO 99 %"), refId="B")],
           "percent", 0, 6, w=24, h=8),
    row(26, "Operación — ¿qué está pasando?", 14),
]
slo_panels[5]["fieldConfig"]["defaults"].pop("min")
slo_panels[5]["fieldConfig"]["defaults"]["max"] = 100
panels = slo_panels + panels

dashboard = {
    "uid": "finance-platform",
    "title": "Finance Platform",
    "description": "Salud de la API de Finance Platform en Kubernetes.",
    "tags": ["finance-platform", "opendays"],
    "timezone": "browser",
    "editable": False,
    "graphTooltip": 1,
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m"]},
    "schemaVersion": 39,
    "version": 1,
    "panels": panels,
}

json.dump(dashboard, sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
