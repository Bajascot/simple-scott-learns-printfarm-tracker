import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GOVEE_API_BASE = "https://developer-api.govee.com"


def get_devices(api_key: str) -> list[dict]:
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{GOVEE_API_BASE}/v1/devices",
                headers={"Govee-API-Key": api_key},
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("devices", [])
    except Exception as exc:
        logger.warning("Failed to fetch Govee devices: %s", exc)
        return []


def get_device_energy(device_id: str, model: str, api_key: str) -> Optional[float]:
    """Return current power draw in watts, or None if unavailable."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{GOVEE_API_BASE}/v1/devices/state",
                headers={"Govee-API-Key": api_key},
                params={"device": device_id, "model": model},
            )
            resp.raise_for_status()
            properties = resp.json().get("data", {}).get("properties", [])
            for prop in properties:
                if "powerConsumption" in prop:
                    return float(prop["powerConsumption"])
    except Exception as exc:
        logger.warning("Failed to get energy for device %s: %s", device_id, exc)
    return None


def poll_govee_energy() -> None:
    """Scheduled every 60 s — accumulate kWh on running print jobs."""
    from backend.config import settings
    from backend.db import SessionLocal
    from backend.models import JobStatusEnum, PrintJob, Printer

    if not settings.GOVEE_API_KEY:
        return

    db = SessionLocal()
    try:
        running_jobs = (
            db.query(PrintJob).filter(PrintJob.status == JobStatusEnum.RUNNING).all()
        )
        if not running_jobs:
            return

        devices = get_devices(settings.GOVEE_API_KEY)
        device_model_map = {d["device"]: d["model"] for d in devices}

        for job in running_jobs:
            printer = db.query(Printer).filter(Printer.id == job.printer_id).first()
            if not printer or not printer.govee_device_id:
                continue
            model = device_model_map.get(printer.govee_device_id)
            if not model:
                continue
            watts = get_device_energy(printer.govee_device_id, model, settings.GOVEE_API_KEY)
            if watts is not None:
                # Polled every 60 s → watts × (60/3600) h = wh; /1000 = kWh increment
                job.energy_kwh = round((job.energy_kwh or 0.0) + watts / 1000 / 60, 6)

        db.commit()
    finally:
        db.close()
