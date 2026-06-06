import pytest
from tests.conftest import make_energy_rate, make_job, make_printer, make_spool


class TestListJobs:
    def test_empty_list(self, client):
        r = client.get("/api/jobs/")
        assert r.status_code == 200
        assert r.json() == []

    def test_pagination_default(self, client):
        p = make_printer(client)
        for _ in range(5):
            make_job(client, printer_id=p["id"])
        r = client.get("/api/jobs/")
        assert len(r.json()) == 5

    def test_pagination_page_size(self, client):
        p = make_printer(client)
        for _ in range(10):
            make_job(client, printer_id=p["id"])
        r = client.get("/api/jobs/?page=1&page_size=3")
        assert len(r.json()) == 3

    def test_pagination_page_2(self, client):
        p = make_printer(client)
        for _ in range(5):
            make_job(client, printer_id=p["id"])
        page1 = client.get("/api/jobs/?page=1&page_size=3").json()
        page2 = client.get("/api/jobs/?page=2&page_size=3").json()
        assert len(page2) == 2
        ids_p1 = {j["id"] for j in page1}
        ids_p2 = {j["id"] for j in page2}
        assert ids_p1.isdisjoint(ids_p2)

    def test_filter_by_printer_id(self, client):
        p1 = make_printer(client, name="P1")
        p2 = make_printer(client, name="P2")
        make_job(client, printer_id=p1["id"])
        make_job(client, printer_id=p2["id"])
        r = client.get(f"/api/jobs/?printer_id={p1['id']}")
        assert all(j["printer_id"] == p1["id"] for j in r.json())
        assert len(r.json()) == 1

    def test_filter_by_status(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        client.patch(f"/api/jobs/{j['id']}", json={"status": "completed"})
        make_job(client, printer_id=p["id"])  # still running

        completed = client.get("/api/jobs/?status=completed").json()
        running = client.get("/api/jobs/?status=running").json()
        assert len(completed) == 1
        assert len(running) == 1

    def test_ordered_by_started_at_desc(self, client):
        p = make_printer(client)
        j1 = make_job(client, printer_id=p["id"])
        j2 = make_job(client, printer_id=p["id"])
        jobs = client.get("/api/jobs/").json()
        assert jobs[0]["id"] == j2["id"]
        assert jobs[1]["id"] == j1["id"]


class TestCreateJob:
    def test_minimal_fields(self, client):
        p = make_printer(client)
        r = client.post("/api/jobs/", json={"printer_id": p["id"]})
        assert r.status_code == 201
        data = r.json()
        assert data["printer_id"] == p["id"]
        assert data["status"] == "running"
        assert data["started_at"] is not None
        assert data["ended_at"] is None
        assert data["filament_cost"] is None
        assert data["total_cost"] is None

    def test_missing_printer_id(self, client):
        r = client.post("/api/jobs/", json={})
        assert r.status_code == 422

    def test_started_at_defaults_to_now(self, client):
        p = make_printer(client)
        r = client.post("/api/jobs/", json={"printer_id": p["id"]})
        assert r.json()["started_at"] is not None

    def test_custom_started_at(self, client):
        p = make_printer(client)
        r = client.post("/api/jobs/", json={
            "printer_id": p["id"],
            "started_at": "2024-01-15T10:00:00",
        })
        assert "2024-01-15" in r.json()["started_at"]

    def test_invalid_status(self, client):
        p = make_printer(client)
        r = client.post("/api/jobs/", json={"printer_id": p["id"], "status": "printing"})
        assert r.status_code == 422


class TestGetJob:
    def test_get_existing(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.get(f"/api/jobs/{j['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == j["id"]

    def test_get_nonexistent(self, client):
        r = client.get("/api/jobs/999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Job not found"


class TestUpdateJob:
    def test_complete_job_sets_ended_at(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"status": "completed"})
        assert r.status_code == 200
        assert r.json()["ended_at"] is not None

    def test_fail_job_sets_ended_at(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"status": "failed"})
        assert r.json()["ended_at"] is not None

    def test_cancel_job_sets_ended_at(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"status": "cancelled"})
        assert r.json()["ended_at"] is not None

    def test_patch_nonexistent(self, client):
        r = client.patch("/api/jobs/999", json={"status": "completed"})
        assert r.status_code == 404

    def test_add_notes(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"notes": "Warped on layer 3"})
        assert r.json()["notes"] == "Warped on layer 3"


class TestDeleteJob:
    def test_delete_existing(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        assert client.delete(f"/api/jobs/{j['id']}").status_code == 204
        assert client.get(f"/api/jobs/{j['id']}").status_code == 404

    def test_delete_nonexistent(self, client):
        assert client.delete("/api/jobs/999").status_code == 404


class TestCostCalculation:
    def test_filament_cost_calculated_on_create(self, client):
        # spool: 1000g for $20 = $0.02/g
        s = make_spool(client, weight_total_g=1000.0, cost_total=20.0)
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"], spool_id=s["id"], filament_used_g=100.0)
        assert j["filament_cost"] == pytest.approx(2.0, abs=0.001)
        assert j["total_cost"] == pytest.approx(2.0, abs=0.001)

    def test_energy_cost_calculated_on_patch(self, client):
        make_energy_rate(client, rate=0.12)
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"energy_kwh": 1.0})
        assert r.json()["energy_cost"] == pytest.approx(0.12, abs=0.001)

    def test_combined_cost(self, client):
        # filament: 500g spool @ $10 → $0.02/g; use 50g → $1.00
        # energy: 0.5 kWh @ $0.20 → $0.10
        # total: $1.10
        make_energy_rate(client, rate=0.20)
        s = make_spool(client, weight_total_g=500.0, cost_total=10.0)
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"], spool_id=s["id"], filament_used_g=50.0)
        r = client.patch(f"/api/jobs/{j['id']}", json={"status": "completed", "energy_kwh": 0.5})
        data = r.json()
        assert data["filament_cost"] == pytest.approx(1.0, abs=0.001)
        assert data["energy_cost"] == pytest.approx(0.10, abs=0.001)
        assert data["total_cost"] == pytest.approx(1.10, abs=0.001)

    def test_no_cost_without_spool(self, client):
        make_energy_rate(client, rate=0.12)
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"], filament_used_g=50.0)
        # filament_used_g without a spool → no filament_cost
        assert j["filament_cost"] is None

    def test_no_cost_without_energy_rate(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"energy_kwh": 1.0})
        # energy_kwh present but no rate record → no energy_cost
        assert r.json()["energy_cost"] is None

    def test_zero_weight_total_guard(self, client):
        # spool with weight_total_g=0 must not cause divide-by-zero
        s = make_spool(client, weight_total_g=0.0, cost_total=20.0)
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"], spool_id=s["id"], filament_used_g=50.0)
        assert j["filament_cost"] is None

    def test_latest_energy_rate_is_used(self, client):
        make_energy_rate(client, rate=0.10, effective_from="2023-01-01")
        make_energy_rate(client, rate=0.20, effective_from="2024-01-01")
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"])
        r = client.patch(f"/api/jobs/{j['id']}", json={"energy_kwh": 1.0})
        assert r.json()["energy_cost"] == pytest.approx(0.20, abs=0.001)
