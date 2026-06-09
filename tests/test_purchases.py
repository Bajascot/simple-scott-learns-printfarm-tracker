import io
import csv as csv_mod

import pytest

from backend.integrations.amazon import is_filament, parse_csv

# ---------------------------------------------------------------------------
# CSV builder helpers
# ---------------------------------------------------------------------------

FIELDNAMES = [
    'ASIN', 'Billing Address', 'Carrier Name & Tracking Number', 'Currency',
    'Gift Message', 'Gift Recipient Contact', 'Gift Sender Name', 'Item Serial Number',
    'Order Date', 'Order ID', 'Order Status', 'Original Quantity', 'Payment Method Type',
    'Product Condition', 'Product Name', 'Purchase Order Number', 'Ship Date',
    'Shipment Item Subtotal', 'Shipment Item Subtotal Tax', 'Shipment Status',
    'Shipping Address', 'Shipping Charge', 'Shipping Option', 'Total Amount',
    'Total Discounts', 'Unit Price', 'Unit Price Tax', 'Website',
]


def make_csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv_mod.DictWriter(buf, fieldnames=FIELDNAMES)
    writer.writeheader()
    for row in rows:
        full_row = {f: 'N/A' for f in FIELDNAMES}
        full_row.update(row)
        writer.writerow(full_row)
    return buf.getvalue().encode('utf-8-sig')


def filament_row(**overrides):
    return {
        'ASIN': 'B01234ABCD',
        'Order ID': '111-1234567-8901234',
        'Order Date': '2024-03-15T10:00:00Z',
        'Product Name': 'HATCHBOX PLA 3D Printer Filament 1.75mm 1kg Spool White',
        'Unit Price': '19.99',
        'Original Quantity': '1',
        **overrides,
    }


# ---------------------------------------------------------------------------
# is_filament unit tests
# ---------------------------------------------------------------------------

class TestIsFilament:
    def test_pla(self):
        assert is_filament("HATCHBOX PLA 3D Printer Filament 1.75mm")

    def test_petg(self):
        assert is_filament("OVERTURE PETG Filament 1.75mm")

    def test_abs(self):
        assert is_filament("Generic ABS Filament 1kg")

    def test_tpu(self):
        assert is_filament("Flexible TPU Filament 95A 1.75mm")

    def test_asa(self):
        assert is_filament("Polymaker ASA Filament UV Resistant")

    def test_wood(self):
        assert is_filament("HATCHBOX Wood 3D Printer Filament 1kg Spool")

    def test_case_insensitive(self):
        assert is_filament("overture petg filament 1.75mm")

    def test_rejects_plastic_substring(self):
        # "Plastic" contains "pla" — must not match
        assert not is_filament("YOOPAI Filament Storage Bag (Plastic 13.2 inch)")

    def test_rejects_no_material(self):
        assert not is_filament("3D Printer Nozzle Cleaning Kit Filament Clog Cleaner")

    def test_rejects_ptfe_tubing(self):
        assert not is_filament("Capricorn PTFE Tubing for 1.75mm Filament")

    def test_rejects_bible(self):
        assert not is_filament("NLT Study Bible (Filament Enabled)")

    def test_rejects_led_bulb(self):
        assert not is_filament("Edison LED Filament Bulb 60W Equivalent")

    def test_rejects_no_filament_keyword(self):
        assert not is_filament("HATCHBOX PLA 3D Printer Spool 1kg White")


# ---------------------------------------------------------------------------
# parse_csv unit tests
# ---------------------------------------------------------------------------

class TestParseCsv:
    def test_parses_single_row(self):
        rows = parse_csv(io.BytesIO(make_csv_bytes([filament_row()])))
        assert len(rows) == 1
        r = rows[0]
        assert r['asin'] == 'B01234ABCD'
        assert r['amazon_order_id'] == '111-1234567-8901234'
        assert r['item_name'] == 'HATCHBOX PLA 3D Printer Filament 1.75mm 1kg Spool White'
        assert r['cost'] == 19.99
        assert str(r['purchase_date']) == '2024-03-15'

    def test_filters_non_filament(self):
        rows_data = [
            filament_row(),
            filament_row(ASIN='BOTHER', **{
                'Product Name': 'PTFE Tubing for 1.75mm Filament',
                'Order ID': '222-0000000-0000000',
            }),
        ]
        rows = parse_csv(io.BytesIO(make_csv_bytes(rows_data)))
        assert len(rows) == 1

    def test_multiplies_qty_into_cost(self):
        rows = parse_csv(io.BytesIO(make_csv_bytes([
            filament_row(**{'Unit Price': '20.99', 'Original Quantity': '2'})
        ])))
        assert rows[0]['cost'] == pytest.approx(41.98)

    def test_skips_bad_date(self):
        rows = parse_csv(io.BytesIO(make_csv_bytes([filament_row(**{'Order Date': 'not-a-date'})])))
        assert rows == []

    def test_skips_bad_price(self):
        rows = parse_csv(io.BytesIO(make_csv_bytes([filament_row(**{'Unit Price': 'free'})])))
        assert rows == []

    def test_empty_csv(self):
        assert parse_csv(io.BytesIO(make_csv_bytes([]))) == []

    def test_multiple_rows(self):
        rows_data = [
            filament_row(ASIN='BAAA', **{'Order ID': '111-AAA'}),
            filament_row(ASIN='BBBB', **{'Order ID': '111-BBB'}),
            filament_row(ASIN='BCCC', **{'Order ID': '111-CCC'}),
        ]
        assert len(parse_csv(io.BytesIO(make_csv_bytes(rows_data)))) == 3


# ---------------------------------------------------------------------------
# GET /api/purchases
# ---------------------------------------------------------------------------

class TestListPurchases:
    def test_empty(self, client):
        r = client.get('/api/purchases')
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_imported_purchases(self, client):
        data = make_csv_bytes([
            filament_row(ASIN='BAAA', **{'Order ID': '111-AAA'}),
            filament_row(ASIN='BBBB', **{'Order ID': '111-BBB'}),
        ])
        client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        r = client.get('/api/purchases')
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_sorted_newest_first(self, client):
        data = make_csv_bytes([
            filament_row(ASIN='BOLD', **{'Order ID': '111-OLD', 'Order Date': '2022-01-01T00:00:00Z'}),
            filament_row(ASIN='BNEW', **{'Order ID': '111-NEW', 'Order Date': '2024-06-01T00:00:00Z'}),
        ])
        client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        items = client.get('/api/purchases').json()
        assert items[0]['purchase_date'] == '2024-06-01'
        assert items[1]['purchase_date'] == '2022-01-01'


# ---------------------------------------------------------------------------
# POST /api/purchases/import/amazon-csv
# ---------------------------------------------------------------------------

class TestImportAmazonCsv:
    def test_happy_path(self, client):
        data = make_csv_bytes([filament_row()])
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        assert r.status_code == 200
        body = r.json()
        assert body['inserted'] == 1
        assert body['skipped'] == 0
        assert body['total_found'] == 1

    def test_skips_duplicates_on_reimport(self, client):
        data = make_csv_bytes([filament_row()])
        client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        assert r.json()['inserted'] == 0
        assert r.json()['skipped'] == 1

    def test_same_order_different_asin_both_imported(self, client):
        data = make_csv_bytes([
            filament_row(ASIN='BAAA'),
            filament_row(ASIN='BBBB'),  # same Order ID, different ASIN
        ])
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        assert r.json()['inserted'] == 2

    def test_non_filament_rows_not_counted(self, client):
        data = make_csv_bytes([
            filament_row(),
            filament_row(ASIN='BOTHER', **{
                'Product Name': 'Nozzle Cleaning Kit Filament Tool',
                'Order ID': '222-9999999-9999999',
            }),
        ])
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        assert r.json()['inserted'] == 1
        assert r.json()['total_found'] == 1

    def test_incremental_import(self, client):
        first = make_csv_bytes([filament_row(ASIN='BAAA', **{'Order ID': '111-AAA'})])
        second = make_csv_bytes([
            filament_row(ASIN='BAAA', **{'Order ID': '111-AAA'}),  # duplicate
            filament_row(ASIN='BBBB', **{'Order ID': '111-BBB'}),  # new
        ])
        client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', first, 'text/csv')})
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', second, 'text/csv')})
        assert r.json()['inserted'] == 1
        assert r.json()['skipped'] == 1
        assert len(client.get('/api/purchases').json()) == 2

    def test_response_has_correct_fields(self, client):
        data = make_csv_bytes([filament_row()])
        r = client.post('/api/purchases/import/amazon-csv', files={'file': ('orders.csv', data, 'text/csv')})
        body = r.json()
        assert 'inserted' in body
        assert 'skipped' in body
        assert 'total_found' in body
