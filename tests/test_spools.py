from tests.conftest import make_spool

VALID_SPOOL = {
    "brand": "Hatchbox",
    "material": "PLA",
    "color": "Red",
    "weight_total_g": 1000.0,
    "weight_remaining_g": 800.0,
    "cost_total": 20.0,
}


class TestListSpools:
    def test_empty_list(self, client):
        r = client.get("/api/spools/")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_all_spools(self, client):
        make_spool(client, color="Red")
        make_spool(client, color="Blue")
        assert len(client.get("/api/spools/").json()) == 2


class TestCreateSpool:
    def test_minimal_fields(self, client):
        r = client.post("/api/spools/", json=VALID_SPOOL)
        assert r.status_code == 201
        data = r.json()
        assert data["brand"] == "Hatchbox"
        assert data["material"] == "PLA"
        assert data["weight_remaining_g"] == 800.0
        assert data["purchase_date"] is None
        assert data["amazon_order_id"] is None

    def test_all_fields(self, client):
        payload = {**VALID_SPOOL, "purchase_date": "2024-03-15", "amazon_order_id": "123-456", "notes": "test"}
        r = client.post("/api/spools/", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["purchase_date"] == "2024-03-15"
        assert data["amazon_order_id"] == "123-456"

    def test_all_valid_materials(self, client):
        for material in ["PLA", "PETG", "ABS", "TPU", "ASA", "Other"]:
            r = client.post("/api/spools/", json={**VALID_SPOOL, "material": material})
            assert r.status_code == 201, f"Expected 201 for material={material}"

    def test_invalid_material(self, client):
        r = client.post("/api/spools/", json={**VALID_SPOOL, "material": "CARBON_FIBER"})
        assert r.status_code == 422

    def test_missing_required_fields(self, client):
        for field in ["brand", "material", "color", "weight_total_g", "weight_remaining_g", "cost_total"]:
            payload = {k: v for k, v in VALID_SPOOL.items() if k != field}
            r = client.post("/api/spools/", json=payload)
            assert r.status_code == 422, f"Expected 422 when {field} is missing"

    def test_zero_weight_total(self, client):
        # zero is a valid float; cost-per-gram calc must guard against divide-by-zero
        r = client.post("/api/spools/", json={**VALID_SPOOL, "weight_total_g": 0.0})
        assert r.status_code == 201


class TestGetSpool:
    def test_get_existing(self, client):
        s = make_spool(client, color="Green")
        r = client.get(f"/api/spools/{s['id']}")
        assert r.status_code == 200
        assert r.json()["color"] == "Green"

    def test_get_nonexistent(self, client):
        r = client.get("/api/spools/999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Spool not found"


class TestUpdateSpool:
    def test_patch_weight_remaining(self, client):
        s = make_spool(client)
        r = client.patch(f"/api/spools/{s['id']}", json={"weight_remaining_g": 500.0})
        assert r.status_code == 200
        assert r.json()["weight_remaining_g"] == 500.0
        assert r.json()["brand"] == s["brand"]  # unchanged

    def test_patch_material(self, client):
        s = make_spool(client)
        r = client.patch(f"/api/spools/{s['id']}", json={"material": "PETG"})
        assert r.status_code == 200
        assert r.json()["material"] == "PETG"

    def test_patch_invalid_material(self, client):
        s = make_spool(client)
        r = client.patch(f"/api/spools/{s['id']}", json={"material": "WOOD"})
        assert r.status_code == 422

    def test_patch_nonexistent(self, client):
        r = client.patch("/api/spools/999", json={"color": "Blue"})
        assert r.status_code == 404


class TestDeleteSpool:
    def test_delete_existing(self, client):
        s = make_spool(client)
        r = client.delete(f"/api/spools/{s['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/spools/{s['id']}").status_code == 404

    def test_delete_nonexistent(self, client):
        assert client.delete("/api/spools/999").status_code == 404
