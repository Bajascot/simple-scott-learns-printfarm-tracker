import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, get_db
from backend.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool ensures all sessions share the same in-memory connection,
# so tables created in reset_db are visible to sessions opened by the app.
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enforce FK constraints in test DB so we catch orphan-record bugs
@event.listens_for(engine, "connect")
def set_sqlite_pragma(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers — reusable factory functions so each test can seed its own data
# ---------------------------------------------------------------------------

def make_printer(client, **kwargs):
    payload = {
        "name": "Test Printer",
        "model": "Creality Ender 3",
        "moonraker_url": "http://192.168.1.10:7125",
        **kwargs,
    }
    r = client.post("/api/printers/", json=payload)
    assert r.status_code == 201
    return r.json()


def make_spool(client, **kwargs):
    payload = {
        "brand": "Hatchbox",
        "material": "PLA",
        "color": "Red",
        "weight_total_g": 1000.0,
        "weight_remaining_g": 800.0,
        "cost_total": 20.0,
        **kwargs,
    }
    r = client.post("/api/spools/", json=payload)
    assert r.status_code == 201
    return r.json()


def make_energy_rate(client, rate=0.12, effective_from="2024-01-01"):
    r = client.post(
        "/api/costs/energy-rates",
        json={"rate_per_kwh": rate, "effective_from": effective_from},
    )
    assert r.status_code == 201
    return r.json()


def make_job(client, printer_id, **kwargs):
    payload = {"printer_id": printer_id, **kwargs}
    r = client.post("/api/jobs/", json=payload)
    assert r.status_code == 201
    return r.json()
