import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.models import JobStatusEnum, PrintJob, Printer

logger = logging.getLogger(__name__)

# Tracks last-known state per printer id to detect transitions
_printer_states: dict[int, str] = {}


def poll_printer(printer: Printer) -> None:
    url = f"{printer.moonraker_url.rstrip('/')}/printer/objects/query"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params="print_stats&display_status")
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Failed to poll printer %s (%s): %s", printer.name, printer.moonraker_url, exc)
        return

    print_stats = data.get("result", {}).get("status", {}).get("print_stats", {})
    state: str = print_stats.get("state", "unknown")
    filament_used_mm: float = print_stats.get("filament_used", 0.0)
    filename: str = print_stats.get("filename", "")

    prev_state = _printer_states.get(printer.id, "unknown")
    _printer_states[printer.id] = state

    db: Session = SessionLocal()
    try:
        if prev_state == "printing" and state in ("complete", "standby", "error", "cancelled"):
            active_job = (
                db.query(PrintJob)
                .filter(
                    PrintJob.printer_id == printer.id,
                    PrintJob.status == JobStatusEnum.RUNNING,
                )
                .order_by(PrintJob.started_at.desc())
                .first()
            )
            if active_job:
                active_job.ended_at = datetime.utcnow()
                active_job.status = (
                    JobStatusEnum.COMPLETED if state == "complete" else JobStatusEnum.FAILED
                )
                if filament_used_mm:
                    # Moonraker reports mm; approximate g assuming 1.75mm PLA ~0.00297 g/mm
                    active_job.filament_used_g = round(filament_used_mm * 0.00297, 2)
                db.commit()
                logger.info("Closed job %d for printer %s → %s", active_job.id, printer.name, active_job.status)

        elif state == "printing" and prev_state != "printing":
            job = PrintJob(
                printer_id=printer.id,
                gcode_filename=filename or None,
                status=JobStatusEnum.RUNNING,
                started_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()
            logger.info("Started job for printer %s, file: %s", printer.name, filename)
    finally:
        db.close()


def poll_all_printers() -> None:
    db: Session = SessionLocal()
    try:
        printers = db.query(Printer).all()
    finally:
        db.close()

    for printer in printers:
        poll_printer(printer)
