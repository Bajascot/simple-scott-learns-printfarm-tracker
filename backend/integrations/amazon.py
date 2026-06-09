import csv
import io
import logging
import re
from datetime import datetime
from typing import IO

logger = logging.getLogger(__name__)

MATERIAL_PATTERN = re.compile(r'\b(PLA|PETG|ABS|TPU|ASA|Wood)\b', re.IGNORECASE)


def is_filament(product_name: str) -> bool:
    return (
        bool(re.search(r'\bfilament\b', product_name, re.IGNORECASE))
        and bool(MATERIAL_PATTERN.search(product_name))
    )


def parse_csv(file: IO[bytes]) -> list[dict]:
    """Parse an Amazon order history CSV and return filament purchase dicts."""
    text = io.TextIOWrapper(file, encoding='utf-8-sig')
    reader = csv.DictReader(text)
    results = []
    for row in reader:
        name = row.get('Product Name', '')
        if not is_filament(name):
            continue
        try:
            raw_date = row.get('Order Date', '')
            purchase_date = datetime.fromisoformat(raw_date.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            logger.warning("Skipping row with unparseable date: %s", raw_date)
            continue
        try:
            unit_price = float(row.get('Unit Price', '0') or '0')
            qty = int(row.get('Original Quantity', '1') or '1')
        except ValueError:
            logger.warning("Skipping row with unparseable price/qty for: %s", name)
            continue
        results.append({
            'asin': row.get('ASIN', '').strip(),
            'amazon_order_id': row.get('Order ID', '').strip(),
            'item_name': name,
            'cost': round(unit_price * qty, 2),
            'purchase_date': purchase_date,
        })
    return results


def import_from_csv(file: IO[bytes], db) -> dict:
    """Parse CSV and persist new filament purchases, skipping duplicates."""
    from backend.models import Purchase

    orders = parse_csv(file)
    inserted = skipped = 0
    for order in orders:
        existing = (
            db.query(Purchase)
            .filter(
                Purchase.amazon_order_id == order['amazon_order_id'],
                Purchase.asin == order['asin'],
            )
            .first()
        )
        if existing:
            skipped += 1
            continue
        db.add(Purchase(**order))
        inserted += 1
    db.commit()

    logger.info("Amazon CSV import: %d inserted, %d skipped", inserted, skipped)
    return {'inserted': inserted, 'skipped': skipped, 'total_found': len(orders)}
