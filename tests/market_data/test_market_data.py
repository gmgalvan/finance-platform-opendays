"""Pruebas del servicio market-data."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "stage-2" / "market-data"))

import market_data  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(market_data, "SLOW_RESPONSE_RATE", 0.0)
    monkeypatch.setattr(market_data, "FAILURE_RATE", 0.0)
    return TestClient(market_data.app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "market-data"


def test_quotes_include_every_instrument(client):
    response = client.get("/quotes")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "market-data"
    assert [quote["symbol"] for quote in body["quotes"]] == ["NOVA", "VERD", "MX50", "BONO10"]
    for quote in body["quotes"]:
        assert set(quote) == {"symbol", "name", "kind", "value", "change_percent"}


@pytest.mark.parametrize("instrument", market_data.INSTRUMENTS, ids=lambda item: item["symbol"])
@pytest.mark.parametrize("now", [0, 1_700_000_000, 1_800_000_123.5])
def test_simulated_price_stays_near_base(instrument, now):
    quote = market_data.simulated_quote(instrument, now)

    limit = instrument["volatility"] * 100
    assert -limit <= quote["change_percent"] <= limit
    assert quote["value"] == pytest.approx(instrument["base"] * (1 + quote["change_percent"] / 100), rel=1e-3)


def test_metrics_count_quote_requests(client):
    client.get("/quotes")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'market_data_requests_total{method="GET",path="/quotes",status="200"}' in response.text


def test_injected_failure_returns_500(client, monkeypatch):
    monkeypatch.setattr(market_data, "FAILURE_RATE", 1.0)

    response = client.get("/quotes")

    assert response.status_code == 500
    assert response.json()["detail"] == "El proveedor de datos no respondió"
