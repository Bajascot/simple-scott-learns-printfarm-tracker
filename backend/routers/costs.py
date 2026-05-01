from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import EnergyRate, JobStatusEnum, PrintJob

router = APIRouter(prefix="/costs", tags=["costs"])


class MonthlySummary(BaseModel):
    year: int
    month: int
    job_count: int
    total_filament_g: Optional[float]
    total_energy_kwh: Optional[float]
    total_filament_cost: Optional[float]
    total_energy_cost: Optional[float]
    total_cost: Optional[float]


class EnergyRateCreate(BaseModel):
    rate_per_kwh: float
    effective_from: date
    label: Optional[str] = None


class EnergyRateResponse(BaseModel):
    id: int
    rate_per_kwh: float
    effective_from: date
    label: Optional[str]

    model_config = {"from_attributes": True}


@router.get("/summary/totals")
def totals_summary(db: Session = Depends(get_db)):
    row = (
        db.query(
            func.count(PrintJob.id).label("job_count"),
            func.sum(PrintJob.filament_used_g).label("total_filament_g"),
            func.sum(PrintJob.energy_kwh).label("total_energy_kwh"),
            func.sum(PrintJob.total_cost).label("total_cost"),
        )
        .filter(PrintJob.status == JobStatusEnum.COMPLETED)
        .first()
    )
    return {
        "job_count": row.job_count or 0,
        "total_filament_g": round(row.total_filament_g or 0.0, 2),
        "total_energy_kwh": round(row.total_energy_kwh or 0.0, 4),
        "total_cost": round(row.total_cost or 0.0, 2),
    }


@router.get("/summary/monthly", response_model=List[MonthlySummary])
def monthly_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    q = (
        db.query(
            func.strftime("%Y", PrintJob.started_at).label("year"),
            func.strftime("%m", PrintJob.started_at).label("month"),
            func.count(PrintJob.id).label("job_count"),
            func.sum(PrintJob.filament_used_g).label("total_filament_g"),
            func.sum(PrintJob.energy_kwh).label("total_energy_kwh"),
            func.sum(PrintJob.filament_cost).label("total_filament_cost"),
            func.sum(PrintJob.energy_cost).label("total_energy_cost"),
            func.sum(PrintJob.total_cost).label("total_cost"),
        )
        .filter(PrintJob.status == JobStatusEnum.COMPLETED)
    )
    if year:
        q = q.filter(func.strftime("%Y", PrintJob.started_at) == str(year))

    rows = (
        q.group_by(
            func.strftime("%Y", PrintJob.started_at),
            func.strftime("%m", PrintJob.started_at),
        )
        .order_by(
            func.strftime("%Y", PrintJob.started_at).desc(),
            func.strftime("%m", PrintJob.started_at).desc(),
        )
        .all()
    )
    return [
        MonthlySummary(
            year=int(r.year),
            month=int(r.month),
            job_count=r.job_count,
            total_filament_g=r.total_filament_g,
            total_energy_kwh=r.total_energy_kwh,
            total_filament_cost=r.total_filament_cost,
            total_energy_cost=r.total_energy_cost,
            total_cost=r.total_cost,
        )
        for r in rows
    ]


@router.get("/energy-rates", response_model=List[EnergyRateResponse])
def list_energy_rates(db: Session = Depends(get_db)):
    return db.query(EnergyRate).order_by(EnergyRate.effective_from.desc()).all()


@router.post("/energy-rates", response_model=EnergyRateResponse, status_code=status.HTTP_201_CREATED)
def create_energy_rate(data: EnergyRateCreate, db: Session = Depends(get_db)):
    rate = EnergyRate(**data.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate
