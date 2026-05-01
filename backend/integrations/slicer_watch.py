import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_observer: Optional[Observer] = None


def _extract_gcode_filament_g(path: Path) -> Optional[float]:
    """Parse filament grams from OrcaSlicer / PrusaSlicer gcode comment headers."""
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                # OrcaSlicer:   ; filament used [g] = 12.34
                if line.startswith("; filament used [g]"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return float(parts[1].strip().split()[0])
                # PrusaSlicer:  ; total filament used [g] = 12.34
                if line.startswith("; total filament used [g]"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return float(parts[1].strip().split()[0])
                # Fallback:     ; filament used = 12345.00mm (12.34g)
                low = line.lower()
                if low.startswith("; filament used") and "(" in line and "g)" in line:
                    gram_str = line.split("(")[-1].replace("g)", "").strip()
                    return float(gram_str)
    except Exception as exc:
        logger.warning("Failed to parse gcode %s: %s", path, exc)
    return None


def _extract_3mf_filament_g(path: Path) -> Optional[float]:
    """Extract filament grams from OrcaSlicer / PrusaSlicer .3mf metadata."""
    candidates = [
        "Metadata/slice_info.config",
        "Metadata/model_settings.config",
        "Metadata/slic3r_pe.config",
        "sliceConfig.xml",
    ]
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            for candidate in candidates:
                if candidate not in names:
                    continue
                with zf.open(candidate) as f:
                    content = f.read().decode("utf-8", errors="replace")
                # Attempt XML parse first
                try:
                    root = ElementTree.fromstring(content)
                    for elem in root.iter():
                        key = (elem.get("key") or "").lower()
                        if "filament_used" in key or "filament used" in key:
                            val = elem.get("value", "")
                            try:
                                g = float(val.rstrip("g").strip())
                                if g > 0:
                                    return g
                            except ValueError:
                                pass
                except ElementTree.ParseError:
                    pass
                # Plain-text fallback
                for line in content.splitlines():
                    low = line.lower()
                    if "filament_used" in low or "filament used" in low:
                        for token in line.split():
                            try:
                                g = float(token.rstrip("g,"))
                                if g > 0:
                                    return g
                            except ValueError:
                                continue
    except Exception as exc:
        logger.warning("Failed to parse .3mf %s: %s", path, exc)
    return None


def _create_draft_job(filename: str, filament_g: Optional[float]) -> None:
    from backend.config import settings
    from backend.db import SessionLocal
    from backend.models import JobStatusEnum, PrintJob

    db = SessionLocal()
    try:
        filament_cost = None
        if filament_g and filament_g > 0:
            # Rough placeholder cost; user should link a spool for accurate pricing
            filament_cost = round(filament_g * 0.02, 4)

        job = PrintJob(
            printer_id=1,  # Default printer; user should reassign via the Jobs UI
            gcode_filename=filename,
            status=JobStatusEnum.RUNNING,
            started_at=datetime.utcnow(),
            filament_used_g=filament_g,
            filament_cost=filament_cost,
            notes="Draft — imported from slicer output folder",
        )
        db.add(job)
        db.commit()
        logger.info("Created draft job for %s (filament: %sg)", filename, filament_g)
    finally:
        db.close()


class SlicerFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        suffix = path.suffix.lower()
        if suffix == ".gcode":
            filament_g = _extract_gcode_filament_g(path)
            _create_draft_job(path.name, filament_g)
        elif suffix == ".3mf":
            filament_g = _extract_3mf_filament_g(path)
            _create_draft_job(path.name, filament_g)


def start_watcher(watch_dir: str) -> None:
    global _observer
    if _observer and _observer.is_alive():
        return
    _observer = Observer()
    _observer.schedule(SlicerFileHandler(), watch_dir, recursive=False)
    _observer.start()
    logger.info("Slicer watcher started on: %s", watch_dir)


def stop_watcher() -> None:
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        _observer.join()
        logger.info("Slicer watcher stopped")
