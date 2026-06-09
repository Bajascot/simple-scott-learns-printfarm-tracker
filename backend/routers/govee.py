from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.integrations.govee import get_device_energy, get_devices

router = APIRouter(prefix="/govee", tags=["govee"])


@router.get("/status")
def govee_status():
    return {"configured": bool(settings.GOVEE_API_KEY)}


@router.get("/devices")
def list_govee_devices():
    if not settings.GOVEE_API_KEY:
        raise HTTPException(status_code=400, detail="GOVEE_API_KEY is not configured")
    devices = get_devices(settings.GOVEE_API_KEY)
    return devices


@router.get("/devices/{device_id}/power")
def device_power(device_id: str, model: str):
    if not settings.GOVEE_API_KEY:
        raise HTTPException(status_code=400, detail="GOVEE_API_KEY is not configured")
    watts = get_device_energy(device_id, model, settings.GOVEE_API_KEY)
    if watts is None:
        raise HTTPException(status_code=503, detail="Power reading unavailable for this device")
    return {"device_id": device_id, "watts": watts}
