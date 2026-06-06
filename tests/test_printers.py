from tests.conftest import make_printer


class TestListPrinters:
    def test_empty_list(self, client):
        r = client.get("/api/printers/")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_all_printers(self, client):
        make_printer(client, name="Printer A")
        make_printer(client, name="Printer B")
        r = client.get("/api/printers/")
        assert r.status_code == 200
        assert len(r.json()) == 2


class TestCreatePrinter:
    def test_minimal_fields(self, client):
        r = client.post("/api/printers/", json={
            "name": "Ender 3",
            "model": "Creality Ender 3",
            "moonraker_url": "http://192.168.1.10:7125",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == 1
        assert data["name"] == "Ender 3"
        assert data["govee_device_id"] is None
        assert data["notes"] is None
        assert "created_at" in data

    def test_all_fields(self, client):
        r = client.post("/api/printers/", json={
            "name": "Ender 3",
            "model": "Creality Ender 3",
            "moonraker_url": "http://192.168.1.10:7125",
            "govee_device_id": "AA:BB:CC:DD",
            "notes": "Test bench printer",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["govee_device_id"] == "AA:BB:CC:DD"
        assert data["notes"] == "Test bench printer"

    def test_missing_name(self, client):
        r = client.post("/api/printers/", json={
            "model": "Creality Ender 3",
            "moonraker_url": "http://192.168.1.10:7125",
        })
        assert r.status_code == 422

    def test_missing_model(self, client):
        r = client.post("/api/printers/", json={
            "name": "Ender 3",
            "moonraker_url": "http://192.168.1.10:7125",
        })
        assert r.status_code == 422

    def test_missing_moonraker_url(self, client):
        r = client.post("/api/printers/", json={
            "name": "Ender 3",
            "model": "Creality Ender 3",
        })
        assert r.status_code == 422

    def test_empty_body(self, client):
        r = client.post("/api/printers/", json={})
        assert r.status_code == 422


class TestGetPrinter:
    def test_get_existing(self, client):
        created = make_printer(client, name="My Printer")
        r = client.get(f"/api/printers/{created['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "My Printer"

    def test_get_nonexistent(self, client):
        r = client.get("/api/printers/999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Printer not found"


class TestUpdatePrinter:
    def test_patch_name(self, client):
        p = make_printer(client)
        r = client.patch(f"/api/printers/{p['id']}", json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"
        assert r.json()["model"] == p["model"]  # unchanged

    def test_patch_govee_id(self, client):
        p = make_printer(client)
        r = client.patch(f"/api/printers/{p['id']}", json={"govee_device_id": "XX:YY"})
        assert r.status_code == 200
        assert r.json()["govee_device_id"] == "XX:YY"

    def test_patch_nonexistent(self, client):
        r = client.patch("/api/printers/999", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_patch_empty_body_is_no_op(self, client):
        p = make_printer(client)
        r = client.patch(f"/api/printers/{p['id']}", json={})
        assert r.status_code == 200
        assert r.json()["name"] == p["name"]


class TestDeletePrinter:
    def test_delete_existing(self, client):
        p = make_printer(client)
        r = client.delete(f"/api/printers/{p['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/printers/{p['id']}").status_code == 404

    def test_delete_nonexistent(self, client):
        r = client.delete("/api/printers/999")
        assert r.status_code == 404

    def test_delete_removes_from_list(self, client):
        p = make_printer(client)
        client.delete(f"/api/printers/{p['id']}")
        assert client.get("/api/printers/").json() == []
