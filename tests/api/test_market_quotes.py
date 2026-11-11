"""La API como intermediaria de market-data (sin base de datos)."""

import httpx

import main

QUOTES = {
    "source": "market-data",
    "as_of": "2026-11-10T20:00:00+00:00",
    "quotes": [{"symbol": "NOVA", "name": "Nova Systems", "kind": "price", "value": 142.5, "change_percent": 0.22}],
}


def fake_market_data(handler):
    return lambda: httpx.Client(transport=httpx.MockTransport(handler), base_url=main.MARKET_DATA_URL)


def test_quotes_are_forwarded_from_market_data(client, monkeypatch):
    requested = []

    def handler(request):
        requested.append(request.url.path)
        return httpx.Response(200, json=QUOTES)

    monkeypatch.setattr(main, "market_data_client", fake_market_data(handler))

    response = client.get("/api/market/quotes")

    assert response.status_code == 200
    assert response.json() == QUOTES
    assert requested == ["/quotes"]


def test_market_data_error_returns_503(client, monkeypatch):
    monkeypatch.setattr(main, "market_data_client", fake_market_data(lambda request: httpx.Response(500)))

    response = client.get("/api/market/quotes")

    assert response.status_code == 503
    assert response.json()["detail"] == "El servicio de cotizaciones no está disponible"


def test_market_data_down_returns_503(client, monkeypatch):
    monkeypatch.setattr(main, "MARKET_DATA_URL", "http://127.0.0.1:1")

    response = client.get("/api/market/quotes")

    assert response.status_code == 503
