from tests.conftest import make_energy_rate, make_job, make_printer, make_spool


class TestEnergyRates:
    def test_empty_list(self, client):
        r = client.get("/api/costs/energy-rates")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_rate(self, client):
        r = client.post("/api/costs/energy-rates", json={
            "rate_per_kwh": 0.15,
            "effective_from": "2024-06-01",
            "label": "Summer rate",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["rate_per_kwh"] == 0.15
        assert data["effective_from"] == "2024-06-01"
        assert data["label"] == "Summer rate"
        assert "id" in data

    def test_create_rate_without_label(self, client):
        r = client.post("/api/costs/energy-rates", json={
            "rate_per_kwh": 0.12,
            "effective_from": "2024-01-01",
        })
        assert r.status_code == 201
        assert r.json()["label"] is None

    def test_missing_rate_per_kwh(self, client):
        r = client.post("/api/costs/energy-rates", json={"effective_from": "2024-01-01"})
        assert r.status_code == 422

    def test_missing_effective_from(self, client):
        r = client.post("/api/costs/energy-rates", json={"rate_per_kwh": 0.12})
        assert r.status_code == 422

    def test_rates_ordered_newest_first(self, client):
        make_energy_rate(client, rate=0.10, effective_from="2023-01-01")
        make_energy_rate(client, rate=0.15, effective_from="2024-01-01")
        make_energy_rate(client, rate=0.20, effective_from="2025-01-01")
        rates = client.get("/api/costs/energy-rates").json()
        dates = [r["effective_from"] for r in rates]
        assert dates == sorted(dates, reverse=True)

    def test_multiple_rates_returned(self, client):
        make_energy_rate(client, rate=0.10, effective_from="2023-01-01")
        make_energy_rate(client, rate=0.15, effective_from="2024-01-01")
        assert len(client.get("/api/costs/energy-rates").json()) == 2


class TestTotalsSummary:
    def test_empty_totals(self, client):
        r = client.get("/api/costs/summary/totals")
        assert r.status_code == 200
        data = r.json()
        assert data["job_count"] == 0
        assert data["total_filament_g"] == 0.0
        assert data["total_energy_kwh"] == 0.0
        assert data["total_cost"] == 0.0

    def test_only_completed_jobs_counted(self, client):
        p = make_printer(client)
        j_done = make_job(client, printer_id=p["id"])
        client.patch(f"/api/jobs/{j_done['id']}", json={"status": "completed"})
        make_job(client, printer_id=p["id"])  # still running — should be excluded

        r = client.get("/api/costs/summary/totals")
        assert r.json()["job_count"] == 1

    def test_failed_and_cancelled_excluded(self, client):
        p = make_printer(client)
        j1 = make_job(client, printer_id=p["id"])
        j2 = make_job(client, printer_id=p["id"])
        client.patch(f"/api/jobs/{j1['id']}", json={"status": "failed"})
        client.patch(f"/api/jobs/{j2['id']}", json={"status": "cancelled"})
        assert client.get("/api/costs/summary/totals").json()["job_count"] == 0

    def test_totals_accumulate(self, client):
        make_energy_rate(client, rate=0.10)
        s = make_spool(client, weight_total_g=1000.0, cost_total=20.0)
        p = make_printer(client)

        j1 = make_job(client, printer_id=p["id"], spool_id=s["id"], filament_used_g=100.0)
        client.patch(f"/api/jobs/{j1['id']}", json={"status": "completed", "energy_kwh": 1.0})

        j2 = make_job(client, printer_id=p["id"], spool_id=s["id"], filament_used_g=200.0)
        client.patch(f"/api/jobs/{j2['id']}", json={"status": "completed", "energy_kwh": 2.0})

        data = client.get("/api/costs/summary/totals").json()
        assert data["job_count"] == 2
        assert abs(data["total_filament_g"] - 300.0) < 0.01
        assert abs(data["total_energy_kwh"] - 3.0) < 0.001


class TestMonthlySummary:
    def test_empty_monthly(self, client):
        r = client.get("/api/costs/summary/monthly")
        assert r.status_code == 200
        assert r.json() == []

    def test_monthly_groups_by_month(self, client):
        p = make_printer(client)
        j1 = make_job(client, printer_id=p["id"], started_at="2024-01-10T10:00:00")
        j2 = make_job(client, printer_id=p["id"], started_at="2024-02-10T10:00:00")
        client.patch(f"/api/jobs/{j1['id']}", json={"status": "completed"})
        client.patch(f"/api/jobs/{j2['id']}", json={"status": "completed"})

        months = client.get("/api/costs/summary/monthly").json()
        assert len(months) == 2
        month_labels = {(m["year"], m["month"]) for m in months}
        assert (2024, 1) in month_labels
        assert (2024, 2) in month_labels

    def test_monthly_filter_by_year(self, client):
        p = make_printer(client)
        j1 = make_job(client, printer_id=p["id"], started_at="2023-06-10T10:00:00")
        j2 = make_job(client, printer_id=p["id"], started_at="2024-06-10T10:00:00")
        client.patch(f"/api/jobs/{j1['id']}", json={"status": "completed"})
        client.patch(f"/api/jobs/{j2['id']}", json={"status": "completed"})

        months_2024 = client.get("/api/costs/summary/monthly?year=2024").json()
        assert len(months_2024) == 1
        assert months_2024[0]["year"] == 2024

    def test_monthly_only_completed(self, client):
        p = make_printer(client)
        j = make_job(client, printer_id=p["id"], started_at="2024-01-10T10:00:00")
        # leave it running
        months = client.get("/api/costs/summary/monthly").json()
        assert months == []

    def test_monthly_job_count(self, client):
        p = make_printer(client)
        for _ in range(3):
            j = make_job(client, printer_id=p["id"], started_at="2024-03-01T10:00:00")
            client.patch(f"/api/jobs/{j['id']}", json={"status": "completed"})

        months = client.get("/api/costs/summary/monthly").json()
        assert months[0]["job_count"] == 3

    def test_monthly_ordered_newest_first(self, client):
        p = make_printer(client)
        for month in ["2024-01", "2024-03", "2024-02"]:
            j = make_job(client, printer_id=p["id"], started_at=f"{month}-01T00:00:00")
            client.patch(f"/api/jobs/{j['id']}", json={"status": "completed"})

        months = client.get("/api/costs/summary/monthly").json()
        month_nums = [m["month"] for m in months]
        assert month_nums == sorted(month_nums, reverse=True)
