import logging

from apscheduler.schedulers.background import BackgroundScheduler

from backend.integrations.govee import poll_govee_energy
from backend.integrations.moonraker import poll_all_printers

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    from backend.config import settings
    from backend.integrations.slicer_watch import start_watcher

    _scheduler.add_job(poll_all_printers, "interval", seconds=30, id="moonraker_poll", max_instances=1)
    _scheduler.add_job(poll_govee_energy, "interval", seconds=60, id="govee_poll", max_instances=1)
    _scheduler.start()
    logger.info("APScheduler started (moonraker=30s, govee=60s)")

    try:
        start_watcher(settings.SLICER_WATCH_DIR)
    except Exception as exc:
        logger.warning("Slicer watcher could not start (dir may not exist on this machine): %s", exc)


def shutdown_scheduler() -> None:
    from backend.integrations.slicer_watch import stop_watcher

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
    stop_watcher()
    logger.info("APScheduler shut down")
