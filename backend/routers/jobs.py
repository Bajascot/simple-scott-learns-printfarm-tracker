from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import EnergyRate, JobStatusEnum, PrintJob, Spool

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    printer_id: int
    spool_id: Optional[int] = None
    gcode_filename: Optional[str] = None
    status: JobStatusEnum = JobStatusEnum.RUNNING
    started_at: Optional[datetime] = None
    filament_used_g: Optional[float] = None
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    spool_id: Optional[int] = None
    status: Optional[JobStatusEnum] = None
    ended_at: Optional[datetime] = None
    filament_used_g: Optional[float] = None
    energy_kwh: Optional[float] = None
    notes: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    printer_id: int
    spool_id: Optional[int]
    gcode_filename: Optional[str]
    status: JobStatusEnum
    started_at: datetime
    ended_at: Optional[datetime]
    filament_used_g: Optional[float]
    energy_kwh: Optional[float]
    filament_cost: Optional[float]
    energy_cost: Optional[float]
    total_cost: Optional[float]
    notes: Optional[str]

    model_config = {"from_attributes": True}


def _recalculate_costs(job: PrintJob, db: Session) -> None:
    filament_cost = None
    if job.filament_used_g is not None and job.spool_id is not None:
        spool = db.query(Spool).filter(Spool.id == job.spool_id).first()
        if spool and spool.weight_total_g > 0:
            cost_per_g = spool.cost_total / spool.weight_total_g
            filament_cost = round(job.filament_used_g * cost_per_g, 4)

    energy_cost = None
    if job.energy_kwh is not None:
        rate = (
            db.query(EnergyRate)
            .order_by(EnergyRate.effective_from.desc())
            .first()
        )
        if rate:
            energy_cost = round(job.energy_kwh * rate.rate_per_kwh, 4)

    job.filament_cost = filament_cost
    job.energy_cost = energy_cost
    if filament_cost is not None or energy_cost is not None:
        job.total_cost = round((filament_cost or 0.0) + (energy_cost or 0.0), 4)


@router.get("", response_model=List[JobResponse])
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    printer_id: Optional[int] = None,
    status: Optional[JobStatusEnum] = None,
    db: Session = Depends(get_db),
):
    q = db.query(PrintJob)
    if printer_id is not None:
        q = q.filter(PrintJob.printer_id == printer_id)
    if status is not None:
        q = q.filter(PrintJob.status == status)
    q = q.order_by(PrintJob.started_at.desc())
    return q.offset((page - 1) * page_size).limit(page_size).all()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    job_data = data.model_dump()
    if job_data.get("started_at") is None:
        job_data["started_at"] = datetime.utcnow()
    job = PrintJob(**job_data)
    _recalculate_costs(job, db)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, data: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    terminal_statuses = {JobStatusEnum.COMPLETED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED}
    if job.status in terminal_statuses and job.ended_at is None:
        job.ended_at = datetime.utcnow()
    _recalculate_costs(job, db)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
