"""Configuración compartida para las pruebas de la API.

Las pruebas marcadas con ``database`` necesitan PostgreSQL. Localmente se
omiten si no hay base de datos; en CI se define ``REQUIRE_DATABASE=1`` para
que fallen en lugar de omitirse.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "app" / "stage-2" / "api"
SCHEMA = ROOT / "app" / "stage-2" / "database" / "init.sql"

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://finance:finance_demo@localhost:55432/finance_platform",
)
sys.path.insert(0, str(API_DIR))

import psycopg  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture(scope="session")
def database():
    try:
        with psycopg.connect(main.DATABASE_URL, connect_timeout=3, autocommit=True) as connection:
            connection.execute(SCHEMA.read_text(encoding="utf-8"))
    except psycopg.OperationalError as error:
        if os.environ.get("REQUIRE_DATABASE") == "1":
            pytest.fail(f"PostgreSQL es obligatorio en este ambiente: {error}")
        pytest.skip("PostgreSQL no está disponible; ejecuta `make test-db-up`")
    return main.DATABASE_URL


@pytest.fixture
def clean_database(database):
    with psycopg.connect(database, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE user_interests, subscriptions, users RESTART IDENTITY CASCADE"
        )
    return database


@pytest.fixture
def subscription_payload():
    return {
        "name": "Ana   López",
        "email": "Ana.Lopez@Example.com",
        "password": "contrasena-segura",
        "topics": ["Mercados", "Economía"],
        "newsletter": True,
    }
