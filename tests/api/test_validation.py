"""Pruebas unitarias: no necesitan base de datos."""

import hashlib
import hmac

import pytest
from pydantic import ValidationError

import main


def test_subscription_request_normalizes_input(subscription_payload):
    subscription_payload["topics"] = ["Mercados", "Mercados", "Economía"]

    request = main.SubscriptionRequest(**subscription_payload)

    assert request.name == "Ana López"
    assert request.email == "ana.lopez@example.com"
    assert request.topics == ["Mercados", "Economía"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "correo-sin-arroba"),
        ("password", "corta"),
        ("topics", ["Criptomonedas"]),
        ("topics", []),
        ("name", " a "),
    ],
)
def test_subscription_request_rejects_invalid_data(subscription_payload, field, value):
    subscription_payload[field] = value

    with pytest.raises(ValidationError):
        main.SubscriptionRequest(**subscription_payload)


def test_invalid_subscription_returns_422_before_touching_database(client, subscription_payload):
    subscription_payload["email"] = "no-es-un-correo"

    response = client.post("/api/subscriptions", json=subscription_payload)

    assert response.status_code == 422


def test_password_hash_uses_pbkdf2_with_random_salt():
    first = main.hash_password("contrasena-segura")
    second = main.hash_password("contrasena-segura")

    assert first != second
    assert "contrasena-segura" not in first

    algorithm, iterations, salt, digest = first.split("$")
    expected = hashlib.pbkdf2_hmac(
        "sha256", b"contrasena-segura", bytes.fromhex(salt), int(iterations)
    ).hex()
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) >= 210_000
    assert hmac.compare_digest(digest, expected)


def test_dashboard_rejects_invalid_email(client):
    response = client.get("/api/dashboard", params={"email": "invalido"})

    assert response.status_code == 400


def test_health_reports_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/none")

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "La base de datos no está disponible"


def test_metrics_are_exposed_in_prometheus_format(client):
    client.get("/api/dashboard", params={"email": "invalido"})

    response = client.get("/api/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "finance_api_requests_total" in response.text
    assert "finance_api_request_duration_seconds" in response.text


def test_tracing_is_disabled_without_otlp_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert main.configure_tracing(main.app) is False
