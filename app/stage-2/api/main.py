import hashlib
import hmac
import os
import re
import secrets
import time
from contextlib import contextmanager

import httpx
import psycopg
from fastapi import FastAPI, HTTPException, Request, Response, status
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://finance:finance_demo@db:5432/finance_platform",
)
MARKET_DATA_URL = os.environ.get("MARKET_DATA_URL", "http://market-data:8000")
ALLOWED_TOPICS = {"Mercados", "Economía", "Finanzas personales", "Tecnología"}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

REQUEST_COUNT = Counter(
    "finance_api_requests_total",
    "Total de solicitudes recibidas por la API",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "finance_api_request_duration_seconds",
    "Duración de las solicitudes de la API",
    ["method", "path"],
)

APP_VERSION = os.environ.get("APP_VERSION", "dev")

app = FastAPI(
    title="Finance Platform API",
    description="API educativa para demostrar una arquitectura de tres capas.",
    version="0.2.0",
)

tracer = trace.get_tracer("finance-api")


def configure_tracing(application: FastAPI) -> bool:
    """Envía trazas por OTLP solo si OTEL_EXPORTER_OTLP_ENDPOINT está definido."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": os.environ.get("OTEL_SERVICE_NAME", "finance-api"),
                "service.version": APP_VERSION,
            }
        )
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    PsycopgInstrumentor().instrument(enable_commenter=False)
    # Propaga la traza en las llamadas HTTP a market-data.
    HTTPXClientInstrumentor().instrument()
    # Los probes y Prometheus llaman /health y /metrics cada pocos segundos:
    # no aportan a las trazas y llenarían Jaeger de ruido.
    FastAPIInstrumentor.instrument_app(application, excluded_urls="health,metrics")
    return True


configure_tracing(app)


class SubscriptionRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    topics: list[str] = Field(min_length=1, max_length=4)
    newsletter: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("El nombre debe contener al menos dos caracteres")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_PATTERN.match(cleaned):
            raise ValueError("El correo electrónico no es válido")
        return cleaned

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: list[str]) -> list[str]:
        unique_values = list(dict.fromkeys(values))
        invalid = set(unique_values) - ALLOWED_TOPICS
        if invalid:
            raise ValueError(f"Temas no permitidos: {', '.join(sorted(invalid))}")
        return unique_values


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


@contextmanager
def database_connection():
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
            yield connection
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible",
        ) from error


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


@app.get("/health")
@app.get("/api/health")
def health():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS healthy")
            cursor.fetchone()
    return {
        "status": "ok",
        "service": "finance-api",
        "version": APP_VERSION,
        "database": "connected",
    }


@app.get("/metrics")
@app.get("/api/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/subscriptions", status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionRequest):
    # PBKDF2 es lento a propósito (210 000 iteraciones); en la traza se ve como
    # el paso que más tarda.
    with tracer.start_as_current_span("hash_password"):
        password_hash = hash_password(payload.password)

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, newsletter)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    password_hash = EXCLUDED.password_hash,
                    newsletter = EXCLUDED.newsletter,
                    updated_at = NOW()
                RETURNING id, name, email, newsletter, created_at
                """,
                (payload.name, payload.email, password_hash, payload.newsletter),
            )
            user = cursor.fetchone()

            cursor.execute("DELETE FROM user_interests WHERE user_id = %s", (user["id"],))
            cursor.executemany(
                "INSERT INTO user_interests (user_id, topic) VALUES (%s, %s)",
                [(user["id"], topic) for topic in payload.topics],
            )

            cursor.execute(
                """
                INSERT INTO subscriptions (user_id, plan, status)
                VALUES (%s, 'finance_plus', 'active')
                ON CONFLICT (user_id) DO UPDATE SET
                    plan = EXCLUDED.plan,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING plan, status, created_at
                """,
                (user["id"],),
            )
            subscription = cursor.fetchone()

    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "newsletter": user["newsletter"],
            "topics": payload.topics,
        },
        "subscription": subscription,
    }


@app.get("/api/dashboard")
def get_dashboard(email: str):
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized_email):
        raise HTTPException(status_code=400, detail="El correo electrónico no es válido")

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.name, u.email, u.newsletter,
                       s.plan, s.status AS subscription_status
                FROM users u
                LEFT JOIN subscriptions s ON s.user_id = u.id
                WHERE u.email = %s
                """,
                (normalized_email,),
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="La cuenta no existe")

            cursor.execute(
                "SELECT topic FROM user_interests WHERE user_id = %s ORDER BY topic",
                (user["id"],),
            )
            topics = [row["topic"] for row in cursor.fetchall()]

    return {"user": {**user, "topics": topics}}


def market_data_client() -> httpx.Client:
    return httpx.Client(timeout=2.0)


@app.get("/api/market/quotes")
def get_market_quotes():
    """Cotizaciones del servicio market-data.

    Si market-data falla, responde 503 y el resto de la API sigue funcionando.
    """
    try:
        with market_data_client() as client:
            response = client.get(f"{MARKET_DATA_URL}/quotes")
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de cotizaciones no está disponible",
        ) from error
    return response.json()
