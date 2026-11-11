"""Pruebas de integración: API + PostgreSQL."""

import psycopg
import pytest

pytestmark = pytest.mark.database


def test_health_checks_database(client, database):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "finance-api",
        "version": "dev",
        "database": "connected",
    }


def test_create_subscription_and_read_dashboard(client, clean_database, subscription_payload):
    created = client.post("/api/subscriptions", json=subscription_payload)

    assert created.status_code == 201
    body = created.json()
    assert body["user"]["email"] == "ana.lopez@example.com"
    assert body["subscription"]["plan"] == "finance_plus"
    assert body["subscription"]["status"] == "active"

    dashboard = client.get("/api/dashboard", params={"email": "ANA.LOPEZ@example.com"})

    assert dashboard.status_code == 200
    user = dashboard.json()["user"]
    assert user["name"] == "Ana López"
    assert user["plan"] == "finance_plus"
    assert user["topics"] == ["Economía", "Mercados"]


def test_subscribing_twice_updates_the_same_user(client, clean_database, subscription_payload):
    client.post("/api/subscriptions", json=subscription_payload)
    subscription_payload["name"] = "Ana María López"
    subscription_payload["topics"] = ["Tecnología"]

    response = client.post("/api/subscriptions", json=subscription_payload)

    assert response.status_code == 201
    with psycopg.connect(clean_database) as connection:
        users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        subscriptions = connection.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    assert users == 1
    assert subscriptions == 1

    dashboard = client.get("/api/dashboard", params={"email": subscription_payload["email"]})
    assert dashboard.json()["user"]["name"] == "Ana María López"
    assert dashboard.json()["user"]["topics"] == ["Tecnología"]


def test_password_is_never_stored_in_plain_text(client, clean_database, subscription_payload):
    client.post("/api/subscriptions", json=subscription_payload)

    with psycopg.connect(clean_database) as connection:
        stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]

    assert stored.startswith("pbkdf2_sha256$")
    assert subscription_payload["password"] not in stored


def test_dashboard_returns_404_for_unknown_account(client, clean_database):
    response = client.get("/api/dashboard", params={"email": "nadie@example.com"})

    assert response.status_code == 404


def test_subscription_trace_includes_password_hash_span(client, clean_database, subscription_payload):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    client.post("/api/subscriptions", json=subscription_payload)

    assert "hash_password" in [span.name for span in exporter.get_finished_spans()]
