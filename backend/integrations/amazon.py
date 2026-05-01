import logging
from datetime import date

logger = logging.getLogger(__name__)

# TODO: Run `playwright install chromium` before enabling this module.
# Real implementation must handle 2FA / OTP, CAPTCHA, and Amazon's rate limiting.
# Consider using a stored session cookie to avoid re-logging-in every run.


async def scrape_orders(email: str, password: str) -> list[dict]:
    """
    Scrape filament orders from Amazon order history.

    Scraping approach (not yet implemented — see TODOs below):
    1. Launch headless Chromium via Playwright async API
    2. Navigate to https://www.amazon.com/ap/signin
    3. Fill `input[name="email"]`, click Continue, fill `input[name="password"]`, click Sign-In
    4. Handle OTP / 2FA page if present (requires human or stored session)
    5. Navigate to https://www.amazon.com/gp/your-account/order-history
    6. Enter "filament" in the search field and submit
    7. For each page of results, iterate `.order` blocks:
         - Order ID:   data-order-id attribute or #order-id-XXXXXX
         - Item name:  .yohtmlc-product-title (first span text)
         - Order date: .a-color-secondary .value  (e.g. "April 5, 2025")
         - Price:      .a-price .a-offscreen      (e.g. "$22.99")
    8. Click "Next page" until no more pages
    9. Return list of dicts with keys:
         amazon_order_id, item_name, cost (float), purchase_date (date object)

    Returns:
        List of order dicts; empty list until implemented.
    """
    # TODO: Uncomment and complete once Playwright is installed:
    #
    # from playwright.async_api import async_playwright
    # import re
    # from datetime import datetime
    #
    # orders = []
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch(headless=True)
    #     page = await browser.new_page()
    #
    #     await page.goto("https://www.amazon.com/ap/signin")
    #     await page.fill('input[name="email"]', email)
    #     await page.click('input[id="continue"]')
    #     await page.wait_for_load_state("networkidle")
    #     await page.fill('input[name="password"]', password)
    #     await page.click('input[id="signInSubmit"]')
    #     await page.wait_for_load_state("networkidle")
    #
    #     # TODO: detect and handle OTP page here
    #
    #     await page.goto("https://www.amazon.com/gp/your-account/order-history")
    #     await page.fill('input[name="searchFilter"]', "filament")
    #     await page.press('input[name="searchFilter"]', "Enter")
    #     await page.wait_for_load_state("networkidle")
    #
    #     while True:
    #         for order_el in await page.query_selector_all(".order"):
    #             order_id = await order_el.get_attribute("data-order-id") or ""
    #             name_el = await order_el.query_selector(".yohtmlc-product-title")
    #             item_name = (await name_el.inner_text()).strip() if name_el else "Unknown"
    #             date_el = await order_el.query_selector(".a-color-secondary .value")
    #             raw_date = (await date_el.inner_text()).strip() if date_el else ""
    #             price_el = await order_el.query_selector(".a-price .a-offscreen")
    #             raw_price = (await price_el.inner_text()).strip() if price_el else "0"
    #             try:
    #                 cost = float(re.sub(r"[^\d.]", "", raw_price))
    #                 purchase_date = datetime.strptime(raw_date, "%B %d, %Y").date()
    #             except ValueError:
    #                 continue
    #             orders.append({
    #                 "amazon_order_id": order_id,
    #                 "item_name": item_name,
    #                 "cost": cost,
    #                 "purchase_date": purchase_date,
    #             })
    #
    #         next_btn = await page.query_selector('li.a-last:not(.a-disabled) a')
    #         if not next_btn:
    #             break
    #         await next_btn.click()
    #         await page.wait_for_load_state("networkidle")
    #
    #     await browser.close()
    # return orders

    logger.info("Amazon scraper stub called — not yet implemented")
    return []


async def import_orders_to_db() -> int:
    """Run scraper and persist new purchase records, skipping duplicates."""
    from backend.config import settings
    from backend.db import SessionLocal
    from backend.models import Purchase

    if not settings.AMAZON_EMAIL or not settings.AMAZON_PASSWORD:
        logger.warning("Amazon credentials not configured in .env")
        return 0

    orders = await scrape_orders(settings.AMAZON_EMAIL, settings.AMAZON_PASSWORD)
    if not orders:
        return 0

    db = SessionLocal()
    inserted = 0
    try:
        for order in orders:
            existing = (
                db.query(Purchase)
                .filter(Purchase.amazon_order_id == order.get("amazon_order_id"))
                .first()
            )
            if existing:
                continue
            purchase = Purchase(
                amazon_order_id=order.get("amazon_order_id"),
                item_name=order["item_name"],
                cost=float(order["cost"]),
                purchase_date=order.get("purchase_date") or date.today(),
            )
            db.add(purchase)
            inserted += 1
        db.commit()
    finally:
        db.close()

    logger.info("Imported %d new Amazon orders", inserted)
    return inserted
