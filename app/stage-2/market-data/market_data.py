"""Servicio de cotizaciones simuladas.

Representa a un proveedor externo de datos de mercado: responde con precios
que cambian con el tiempo y con una latencia variable. Es un servicio aparte
porque los datos de mercado tienen otra fuente, otro ritmo de cambio y otro
patrón de carga que las cuentas y suscripciones.
"""

import asyncio
import math
import os
import random
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

APP_VERSION = os.environ.get("APP_VERSION", "dev")
SLOW_RESPONSE_RATE = float(os.environ.get("SLOW_RESPONSE_RATE", "0.05"))
# Para la demo de SRE: proporción de solicitudes que fallan a propósito
# (simula un mal cambio de configuración). 0 = sin fallas.
FAILURE_RATE = float(os.environ.get("FAILURE_RATE", "0"))

INSTRUMENTS = [
    {"symbol": "NOVA", "name": "Nova Systems", "base": 142.18, "kind": "price", "volatility": 0.018},
    {"symbol": "VERD", "name": "Verde Energía", "base": 86.42, "kind": "price", "volatility": 0.012},
    {"symbol": "MX50", "name": "Índice México 50", "base": 53104.0, "kind": "index", "volatility": 0.007},
    {"symbol": "BONO10", "name": "Bono 10 años", "base": 9.31, "kind": "rate", "volatility": 0.002},
]

REQUEST_COUNT = Counter(
    "market_data_requests_total",
    "Total de solicitudes recibidas por market-data",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "market_data_request_duration_seconds",
    "Duración de las solicitudes de market-data",
    ["method", "path"],
)

app = FastAPI(
    title="Market Data",
    description="Cotizaciones simuladas para Finance Platform.",
    version="0.1.0",
)
tracer = trace.get_tracer("market-data")


def configure_tracing(application: FastAPI) -> bool:
    """Envía trazas por OTLP solo si OTEL_EXPORTER_OTLP_ENDPOINT está definido."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": os.environ.get("OTEL_SERVICE_NAME", "market-data"),
                "service.version": APP_VERSION,
            }
        )
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(application, excluded_urls="health,metrics")
    return True


configure_tracing(app)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    started_at = time.perf_counter()
    response_status = 500
    try:
        response = await call_next(request)
        response_status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path, str(response_status)).inc()
        REQUEST_DURATION.labels(request.method, path).observe(time.perf_counter() - started_at)


def simulated_quote(instrument: dict, now: float) -> dict:
    """Precio que oscila suavemente alrededor del valor base."""
    phase = sum(ord(char) for char in instrument["symbol"])
    wave = math.sin(now / 90 + phase) * 0.6 + math.sin(now / 17 + phase * 2) * 0.4
    change = wave * instrument["volatility"]
    value = instrument["base"] * (1 + change)
    return {
        "symbol": instrument["symbol"],
        "name": instrument["name"],
        "kind": instrument["kind"],
        "value": round(value, 2),
        "change_percent": round(change * 100, 2),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "market-data", "version": APP_VERSION}


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/quotes")
async def quotes():
    # Simula la consulta al proveedor externo: normalmente 15-60 ms y, de vez
    # en cuando, una respuesta lenta que se distingue en las trazas.
    slow = random.random() < SLOW_RESPONSE_RATE
    delay = random.uniform(0.25, 0.4) if slow else random.uniform(0.015, 0.06)
    with tracer.start_as_current_span("consultar_proveedor") as span:
        span.set_attribute("market_data.provider", "simulado")
        span.set_attribute("market_data.slow_response", slow)
        await asyncio.sleep(delay)
        if random.random() < FAILURE_RATE:
            span.set_attribute("market_data.injected_failure", True)
            raise HTTPException(status_code=500, detail="El proveedor de datos no respondió")

    now = time.time()
    return {
        "source": "market-data",
        "as_of": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "quotes": [simulated_quote(instrument, now) for instrument in INSTRUMENTS],
    }
